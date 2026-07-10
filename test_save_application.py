"""Test for saving controlled assessment results to postgresql"""


from pprint import pprint 

from agent.controlled_assessment import run_controlled_home_loan_assessment

from database.db import initialize_database

from database.repository import(

    create_application_record,
    get_application_record,
    list_applications
)
from test_controlled_assessment import APPROVED_CASE ,REJECTED_CASE

def save_and_print(case_name:str,application:dict):
      print(f"\n================ {case_name} ================")

      result=run_controlled_home_loan_assessment(application)

      application_id=create_application_record(result)
      print("Saved Application ID:",application_id)

      saved_record=get_application_record(application_id)
      print("\nSaved Record:")
      pprint(saved_record)

      return application_id


if __name__ == "__main__":
    initialize_database()

    approved_id = save_and_print("APPROVED CASE", APPROVED_CASE)
    rejected_id = save_and_print("REJECTED CASE", REJECTED_CASE)

    print("\n================ ALL APPLICATIONS ================")
    pprint(list_applications())

    print("\nCreated IDs:")
    print("Approved:", approved_id)
    print("Rejected:", rejected_id)

 
