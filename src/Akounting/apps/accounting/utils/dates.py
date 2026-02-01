import jdatetime


def add_month_to_jalali_date(jdate):
    year = jdate.year
    month = jdate.month + 1
    day = jdate.day

    if month > 12:
        month = 1
        year += 1

    # Prevent invalid days (e.g. 31 in 30-day months)
    try:
        new_date = jdatetime.date(year, month, day)
    except ValueError:
        new_date = jdatetime.date(year, month, 29)  # یا آخر ماه قبلی رو بگیر

    return new_date