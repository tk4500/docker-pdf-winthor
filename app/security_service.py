from fastapi import Depends, HTTPException, status
from auth import get_current_user
from models import User

class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, user: User = Depends(get_current_user)):
        # 1. Se for Super Admin hardcoded (opcional), passa tudo
        if user.username == "admin_master": 
            return True

        # 2. Verifica se o usuário tem role
        if not user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário sem perfil de acesso atribuído."
            )

        # 3. Varre as permissões da Role do usuário
        user_permissions = [p.slug for p in user.role.permissions]

        if self.required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sem permissão necessária: {self.required_permission}"
            )
        
        return True