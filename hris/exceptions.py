class InitializationError(Exception):
    pass


class RoleError(Exception):
    pass


class UserNotApprover(Exception):
    pass


class InvalidLeaveRequestAction(Exception):
    pass


class InvalidApproverPermission(Exception):
    pass


class InvalidApproverResponse(Exception):
    pass


class PersonalFilesBlockNotFound(Exception):
    pass
