from pydantic import BaseModel, EmailStr, constr

# -----------------------------------------
# Auth
# -----------------------------------------
class LoginForm(BaseModel):
    email: EmailStr
    password: constr(min_length=8)


class RegisterForm(BaseModel):
    email: EmailStr
    username: constr(min_length=3, max_length=30)
    password: constr(min_length=8)

# -----------------------------------------
# 2FA
# -----------------------------------------
class Verify2FAForm(BaseModel):
    code: constr(min_length=6, max_length=6)
