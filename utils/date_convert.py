import datetime, pytz


def gmt7now(dt_utc=None):
    dt_utc = dt_utc if dt_utc != None else datetime.datetime.utcnow()  # utcnow class method
    dt_rep = dt_utc.replace(tzinfo=pytz.UTC)  # replace method
    dt_gmt7 = dt_rep.astimezone(pytz.timezone("Asia/Jakarta"))  # astimezone method [gmt++7]
    return dt_gmt7
