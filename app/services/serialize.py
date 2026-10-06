from sqlalchemy import inspect


def to_dict(obj):
    """Turns a SQLAlchemy row object into a plain dictionary so FastAPI can return it as JSON.

    Uses getattr() per column (not obj.__dict__) because SQLAlchemy "expires" every loaded
    object in a session after each db.commit(). Reading __dict__ directly would return stale/
    empty data for anything committed before the last commit in a loop; getattr() re-fetches
    the value properly even if it was expired.
    """
    columns = inspect(obj.__class__).columns.keys()
    return {column: getattr(obj, column) for column in columns}


def to_dict_list(objs):
    return [to_dict(o) for o in objs]
