from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.template import Template
from app.models.user import User
from app.schemas.template import TemplateCreate, TemplateOut, TemplateUpdate

router = APIRouter(prefix="/templates", tags=["templates"])


def _get_owned(db: Session, user: User, template_id: int) -> Template:
    template = db.get(Template, template_id)
    if template is None or template.user_id != user.id:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.get("", response_model=list[TemplateOut])
def list_templates(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.scalars(
        select(Template).where(Template.user_id == user.id).order_by(Template.id.desc())
    ).all()


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    data: TemplateCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = Template(user_id=user.id, name=data.name, payload=data.payload)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(
    template_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned(db, user, template_id)


@router.put("/{template_id}", response_model=TemplateOut)
def update_template(
    template_id: int,
    data: TemplateUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = _get_owned(db, user, template_id)
    if data.name is not None:
        template.name = data.name
    if data.payload is not None:
        template.payload = data.payload
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = _get_owned(db, user, template_id)
    db.delete(template)
    db.commit()
