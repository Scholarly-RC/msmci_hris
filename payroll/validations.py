from decimal import Decimal


def minimum_wage_update_validation(data, minimum_wage):
    """
    Validates the proposed update to the minimum wage. Checks if the new value matches the current minimum wage,
    handles confirmation requirements, and updates the context with appropriate messages for success or errors.
    """
    context = {}
    minimum_wage_basic_salary = Decimal(data.get("minimum_wage_basic_salary", "0.00"))

    if minimum_wage_basic_salary == minimum_wage.amount:
        context["error"] = (
            "The value you entered matches the current minimum wage. Please enter a different amount."
        )
        return context

    if "for_confirmation" in data:
        context.update(
            {
                "show_confirmation": True,
                "minimum_wage_value": minimum_wage_basic_salary,
            }
        )
        return context

    if "confirmation_box" not in data:
        context.update(
            {
                "show_confirmation": True,
                "confirmation_error": "Please check the box to confirm your changes.",
                "minimum_wage_value": minimum_wage_basic_salary,
            }
        )
        return context

    context["success"] = True
    return context
