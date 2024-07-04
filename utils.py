from datetime import datetime, timedelta

def mjd_to_utc(mjd, trkl):
    # Split into MJD and seconds
    mjd, day_fraction = divmod(mjd, 1)
    seconds_in_day = day_fraction * 86400

    # Convert MJD to date (MJD 0 corresponds to 1858-11-17)
    mjd_start = datetime(1858, 11, 17)
    date = mjd_start + timedelta(days=mjd)

    # Convert seconds to time and add trkl seconds
    time = (mjd_start + timedelta(seconds=seconds_in_day + trkl)).time()

    # Combine date and time
    combined_datetime = datetime.combine(date, time)

    # Format the new datetime object back into a string
    return combined_datetime.strftime("%Y-%m-%d %H:%M:%S")


def is_it_today():
    current_utc_time = datetime.utcnow()
    current_local_time = current_utc_time + timedelta(hours=5, minutes=30)
    # Check if the local time is on or after 5:30 AM
    return current_local_time.hour > 5 or (current_local_time.hour == 5 and current_local_time.minute >= 30)


def extract_time_from_filename(filename):
    """
    Extracts and converts the time part of the filename to a datetime object.
    Assumes filename format is 'IRNPLI60299.HHMMSS'.
    """
    time_part = filename.split('.')[-1]  # Get the last part after the '.'
    return datetime.strptime(time_part, "%H%M%S")  # Convert to datetime object for easy comparison


def mjd_today():
    # Calculate today's Modified Julian Date.
    jd = datetime.utcnow() + timedelta(hours=5, minutes=30)
    mjd = jd.toordinal() + 1721424.5 - 2400000.5
    return int(mjd)
