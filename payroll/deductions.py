from decimal import Decimal

from payroll.utils import (
    convert_string_to_decimal_list,
    get_deduction_configuration_object,
)


class Sss:
    def __init__(self, salary):
        self.salary = salary
        sss_deduction_configuration = get_deduction_configuration_object().sss_config()
        sss_deduction_configuration_data = sss_deduction_configuration.get("data")
        self.min_compensation = Decimal(
            sss_deduction_configuration_data.get("min_compensation")
        )
        self.max_compensation = Decimal(
            sss_deduction_configuration_data.get("max_compensation")
        )
        self.min_contribution = Decimal(
            sss_deduction_configuration_data.get("min_contribution")
        )
        self.max_contribution = Decimal(
            sss_deduction_configuration_data.get("max_contribution")
        )
        self.contribution_difference = Decimal(
            sss_deduction_configuration_data.get("contribution_difference")
        )

    def get_employee_deduction(self):
        if self.salary < self.min_compensation:
            return self.min_contribution
        if self.salary > self.max_compensation:
            return self.max_contribution

        def _calculate_employee_contribution(salary, min_compensation, contribution):
            if salary >= min_compensation and salary < min_compensation + 500:
                return contribution + self.contribution_difference

            return _calculate_employee_contribution(
                salary,
                min_compensation + 500,
                contribution + self.contribution_difference,
            )

        return _calculate_employee_contribution(
            self.salary, self.min_compensation, self.min_contribution
        )


class Philhealth:
    def __init__(self, salary):
        self.salary = salary
        philhealth_deduction_configuration = (
            get_deduction_configuration_object().philhealth_config()
        )
        philhealth_deduction_configuration_data = (
            philhealth_deduction_configuration.get("data")
        )
        self.min_compensation = Decimal(
            philhealth_deduction_configuration_data.get("min_compensation")
        )
        self.max_compensation = Decimal(
            philhealth_deduction_configuration_data.get("max_compensation")
        )
        self.min_contribution = Decimal(
            philhealth_deduction_configuration_data.get("min_contribution")
        )
        self.max_contribution = Decimal(
            philhealth_deduction_configuration_data.get("max_contribution")
        )
        self.rate = Decimal(philhealth_deduction_configuration_data.get("rate")) / 100

    def get_employee_deduction(self):
        if self.salary < self.min_compensation:
            return self.min_contribution

        if self.salary > self.max_compensation:
            return self.max_contribution

        return self.salary * (self.rate / 2)


class Tax:
    def __init__(self, salary):
        self.salary = salary
        tax_deduction_configuration = get_deduction_configuration_object().tax_config()
        tax_deduction_configuration_data = tax_deduction_configuration.get("data")
        self.compensation_range = convert_string_to_decimal_list(
            tax_deduction_configuration_data.get("compensation_range", "")
        )
        self.percentage = convert_string_to_decimal_list(
            tax_deduction_configuration_data.get("percentage", "")
        )
        self.base_tax = convert_string_to_decimal_list(
            tax_deduction_configuration_data.get("base_tax", "")
        )

    def get_employee_deduction(self):
        salary = self.salary
        # Loop through the compensation ranges to find the correct bracket
        for i in range(len(self.compensation_range)):
            if salary <= self.compensation_range[i]:
                # Calculate the tax based on the bracket found
                if i == 0:
                    return Decimal(0.00)
                else:
                    compensation_level = self.compensation_range[i - 1]
                    percentage = self.percentage[i - 1]
                    base_tax = self.base_tax[i - 1]
                    additional_tax = (salary - (compensation_level + 1)) * (
                        percentage / 100
                    )
                    return base_tax + additional_tax
        # If salary exceeds the highest bracket, handle it
        compensation_level = self.compensation_range[-1]
        percentage = self.percentage[-1]
        base_tax = self.base_tax[-1]
        additional_tax = (salary - compensation_level) * (percentage / 100)
        return Decimal(base_tax + additional_tax)


class PagIbig:
    def __init__(self):
        pagibig_deduction_configuration = (
            get_deduction_configuration_object().pagibig_config()
        )
        pagibig_deduction_configuration_data = pagibig_deduction_configuration.get(
            "data"
        )
        self.amount = Decimal(pagibig_deduction_configuration_data.get("amount"))

    def get_employee_deduction(self):
        return self.amount / 2
