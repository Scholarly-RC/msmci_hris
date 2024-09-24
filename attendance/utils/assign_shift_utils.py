def get_employee_assignments(current_daily_shift_record, shifts, employees):
    """
    Retrieves employee assignments for each shift and returns a list of assignments
    along with a list of all assigned user IDs.
    """
    employee_assignments = []
    list_of_assigned_user_ids = []
    for shift in shifts:
        user_id_list_queryset = current_daily_shift_record.shifts.filter(
            shift=shift,
        ).values_list("user__id", flat=True)
        list_of_ids = [id for id in user_id_list_queryset]
        assigned_users = employees.filter(id__in=list_of_ids)
        list_of_assigned_user_ids = list_of_assigned_user_ids + list_of_ids
        employee_assignments.append({"shift": shift, "assigned_users": assigned_users})

    return employee_assignments, list_of_assigned_user_ids
