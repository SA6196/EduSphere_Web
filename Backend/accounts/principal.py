from dataclasses import dataclass


@dataclass(frozen=True)
class LMSPrincipal:
    user_id: int
    username: str
    email: str
    role: str
    account_status: str
    student_id: int | None = None
    instructor_id: int | None = None
    admin_id: int | None = None

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def id(self):
        return self.user_id
