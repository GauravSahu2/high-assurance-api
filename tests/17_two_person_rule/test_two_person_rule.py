import pytest

def verify_deployment_authorization(modified_files, approvers):
    # Define highly sensitive files that interns/juniors cannot push alone
    CRITICAL_PATHS = ["infra/terraform", "src/auth", "src/database_migrations"]
    
    # Check if any critical files were touched
    touches_critical_code = any(any(path in file for path in CRITICAL_PATHS) for file in modified_files)
    
    if touches_critical_code:
        # ATOMIC RULE: Must have at least one Senior/Lead approval
        senior_approvers = [user for user, role in approvers.items() if role in ["Senior", "Lead", "Staff"]]
        if len(senior_approvers) == 0:
            return False, "Deployment Blocked: Critical infrastructure requires Senior authorization."
            
    return True, "Deployment Authorized."

def test_deployment_authorization():
    # Scenario 1: Junior developer tries to push a database migration alone
    modified_files = ["src/database_migrations/v2_drop_columns.sql"]
    approvers = {"dev_intern": "Junior"} # Only the intern approved it
    
    is_authorized, msg = verify_deployment_authorization(modified_files, approvers)
    assert not is_authorized, "CRITICAL FAIL: Pipeline allowed junior to deploy critical code unreviewed!"
    
    # Scenario 2: Junior pairs with a Senior, who approves the PR
    approvers["senior_gaurav"] = "Senior"
    is_authorized, msg = verify_deployment_authorization(modified_files, approvers)
    assert is_authorized, "CRITICAL FAIL: Pipeline blocked a properly authorized deployment."
    
    print("\n[SUCCESS] Two-Person Rule enforced. Critical code requires Senior sign-off.")
