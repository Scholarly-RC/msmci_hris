#!/bin/bash

echo "Loading initial data..."

# Install pymysql if not already installed
pip install pymysql

# Load initial data
# python manage.py loaddata db_data

# Run initialization commands
python manage.py configure_minimum_wage_settings --amount 10520
python manage.py configure_deductions_settings
python manage.py configure_mp2_settings
python manage.py install_performance_evaluation_questionnaires
python manage.py set_user_with_role_to_employee
python manage.py set_usernames
python manage.py initialize_user_leave_credit

echo "Initial data loaded successfully."