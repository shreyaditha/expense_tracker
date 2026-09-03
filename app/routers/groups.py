"""
routers/groups.py
-----------------
CRUD for groups and group membership management.

Authorization rules:
  - Any authenticated user can create a group (they become the creator + first member)
  - Only group members can view the group
  - Only the group creator can update or delete the group
  - Group members can add other users; only the creator can remove members
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.dependencies import get_db, get_current_user

router = APIRouter(prefix="/groups", tags=["Groups"])


# ---------------------------------------------------------------------------
# Helper: fetch group or 404
# ---------------------------------------------------------------------------
def get_group_or_404(group_id: int, db: Session) -> models.Group:
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found.")
    return group


def require_member(group: models.Group, user_id: int):
    """Raise 403 if user is not a member of the group."""
    is_member = any(m.user_id == user_id for m in group.members)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group.",
        )


def require_creator(group: models.Group, user_id: int):
    """Raise 403 if user is not the group creator."""
    if group.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group creator can perform this action.",
        )


# ===========================================================================
# POST /groups/
# ===========================================================================
@router.post("/", response_model=schemas.GroupOut, status_code=201)
def create_group(
    data: schemas.GroupCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new group. The creator is automatically added as the first member."""
    group = models.Group(
        name=data.name,
        description=data.description,
        created_by=current_user.id,
    )
    db.add(group)
    db.flush()  # get group.id before committing

    # Auto-add the creator as a member
    membership = models.GroupMember(group_id=group.id, user_id=current_user.id)
    db.add(membership)
    db.commit()
    db.refresh(group)
    return group


# ===========================================================================
# GET /groups/
# ===========================================================================
@router.get("/", response_model=list[schemas.GroupOut])
def list_my_groups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all groups the current user is a member of."""
    # Join Group → GroupMember to filter by membership
    groups = (
        db.query(models.Group)
        .join(models.GroupMember, models.Group.id == models.GroupMember.group_id)
        .filter(models.GroupMember.user_id == current_user.id)
        .all()
    )
    return groups


# ===========================================================================
# GET /groups/{group_id}
# ===========================================================================
@router.get("/{group_id}", response_model=schemas.GroupOut)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get group details. Only members can view the group."""
    group = get_group_or_404(group_id, db)
    require_member(group, current_user.id)
    return group


# ===========================================================================
# PUT /groups/{group_id}
# ===========================================================================
@router.put("/{group_id}", response_model=schemas.GroupOut)
def update_group(
    group_id: int,
    data: schemas.GroupUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update group name or description. Only the creator can do this."""
    group = get_group_or_404(group_id, db)
    require_creator(group, current_user.id)

    # Only update fields that were actually provided in the request body
    if data.name is not None:
        group.name = data.name
    if data.description is not None:
        group.description = data.description

    db.commit()
    db.refresh(group)
    return group


# ===========================================================================
# DELETE /groups/{group_id}
# ===========================================================================
@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Delete a group and all its expenses. Only the creator can do this.
    Returns 204 No Content on success (standard REST convention for DELETE).
    """
    group = get_group_or_404(group_id, db)
    require_creator(group, current_user.id)
    db.delete(group)
    db.commit()


# ===========================================================================
# GET /groups/{group_id}/members
# ===========================================================================
@router.get("/{group_id}/members", response_model=list[schemas.GroupMemberOut])
def list_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all members of a group. Only members can view this."""
    group = get_group_or_404(group_id, db)
    require_member(group, current_user.id)
    return group.members


# ===========================================================================
# POST /groups/{group_id}/members
# ===========================================================================
@router.post("/{group_id}/members", response_model=schemas.GroupMemberOut, status_code=201)
def add_member(
    group_id: int,
    data: schemas.AddMemberRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Add a user to the group. Any existing member can invite others."""
    group = get_group_or_404(group_id, db)
    require_member(group, current_user.id)

    # Make sure the invited user exists
    invited_user = db.query(models.User).filter(models.User.id == data.user_id).first()
    if not invited_user:
        raise HTTPException(status_code=404, detail="User to add not found.")

    # Check they're not already a member
    already_member = any(m.user_id == data.user_id for m in group.members)
    if already_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this group.",
        )

    membership = models.GroupMember(group_id=group_id, user_id=data.user_id)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


# ===========================================================================
# DELETE /groups/{group_id}/members/{user_id}
# ===========================================================================
@router.delete("/{group_id}/members/{user_id}", status_code=204)
def remove_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Remove a member from the group. Only the creator can remove members."""
    group = get_group_or_404(group_id, db)
    require_creator(group, current_user.id)

    if user_id == group.created_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the group creator.",
        )

    membership = (
        db.query(models.GroupMember)
        .filter(
            models.GroupMember.group_id == group_id,
            models.GroupMember.user_id == user_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="User is not a member of this group.")

    db.delete(membership)
    db.commit()
