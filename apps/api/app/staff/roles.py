from enum import StrEnum


class Department(StrEnum):
    SALES = "sales"
    CODING = "coding"


class StaffRole(StrEnum):
    CEO = "ceo"
    ADMIN = "admin"
    SALES_LEAD = "sales_lead"
    SALES = "sales"
    CODING = "coding"
