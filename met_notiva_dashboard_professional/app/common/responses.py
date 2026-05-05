from flask import jsonify


def ok(data=None, **extra):
    payload = {"success": True, "data": data if data is not None else []}
    payload.update(extra)
    return jsonify(payload)


def fail(message: str, status: int = 500):
    return jsonify({"success": False, "error": message, "data": []}), status
