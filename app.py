import os
from datetime import datetime, date
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from collections import defaultdict
from pydantic import ValidationError

from models import (
    AssignmentCreate,
    AssignmentUpdate,
    assignment_to_dict,
    assignment_update_to_dict,
    serialize_assignment
)

load_dotenv()
app = Flask(__name__)
# Work in Progress: Use secret key for user authentication
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
client = MongoClient(
    os.getenv("MONGO_URI"),
    username=os.getenv("MONGO_USER"),
    password=os.getenv("MONGO_PASS"),
)
db = client["homeworkdb"]
col = db["assignments"]

def group_by_date(assignments):
    """Group assignments by due date with formatted labels"""
    groups = defaultdict(list)
    for a in assignments:
        due = a.get('due_date')
        try:
            # Handle datetime objects
            if isinstance(due, datetime):
                label = due.strftime("%a, %b %d")
            # Handle date objects
            elif isinstance(due, date):
                label = due.strftime("%a, %b %d")
            # Handle string dates (from serialization)
            elif isinstance(due, str):
                due_date = datetime.strptime(due, "%Y-%m-%d")
                label = due_date.strftime("%a, %b %d")
            else:
                label = "Unknown"
        except (ValueError, AttributeError):
            label = "Unknown"
        groups[label].append(a)
    return groups

with app.app_context():
    col.create_index([("due_date", 1)])
    col.create_index([("created_at", -1)])

@app.get("/")
def index():
    cursor = col.find({}).sort([("due_date", 1), ("created_at", -1)])
    assignments = [serialize_assignment(doc) for doc in cursor]
    
    grouped_assignments = group_by_date(assignments)
    
    return render_template("index.html", grouped_assignments=grouped_assignments, has_assignments=len(assignments) > 0)

@app.route("/add", methods=["GET", "POST"])
def add_assignment():
    """
    Route for GET and POST requests to the add assignment page.
    GET: Displays a form users can fill out to create a new assignment.
    POST: Accepts the form submission data for a new assignment and saves it to the database.
    Returns:
        GET: rendered template (str): The rendered HTML template.
        POST: redirect (Response): A redirect response to the home page.
    """
    if request.method == "POST":
        try:
            # If priority is not provided, default to 2
            priority_str = request.form.get("priority", "").strip()
            priority = int(priority_str) if priority_str else 2
            
            assignment_data = AssignmentCreate(
                title=request.form.get("title", ""),
                course=request.form.get("course", ""),
                notes=request.form.get("notes", ""),
                due_date=date.fromisoformat(request.form.get("due_date", "")),
                priority=priority,
                completed=False
            )
            
            doc = assignment_to_dict(assignment_data)
            col.insert_one(doc)
            
            flash("Assignment created successfully!", "success")
            return redirect(url_for("index"))
            
        except ValueError as e:
            flash(f"Error: Invalid date format - {str(e)}", "error")
            return render_template("add_assignment.html"), 400
        except ValidationError as e:
            errors = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
            flash(f"Validation error: {errors}", "error")
            return render_template("add_assignment.html"), 400
    
    return render_template("add_assignment.html")

@app.post("/toggle/<string:assignment_id>")
def toggle_assignment(assignment_id):
    """Toggle the completed status of an assignment"""
    try:
        oid = ObjectId(assignment_id)
    except Exception:
        return "Invalid assignment ID", 400
    
    doc = col.find_one({"_id": oid})
    if not doc:
        return "Assignment not found", 404
    
    new_completed = not bool(doc.get("completed", False))
    col.update_one(
        {"_id": oid},
        {"$set": {"completed": new_completed, "updated_at": datetime.utcnow()}}
    )
    
    return redirect(url_for("index"))

@app.post("/delete/<string:assignment_id>")
def delete_assignment(assignment_id):
    """Delete an assignment"""
    try:
        oid = ObjectId(assignment_id)
    except Exception:
        return "Invalid assignment ID", 400
    
    col.delete_one({"_id": oid})
    return redirect(url_for("index"))

@app.route("/edit/<string:assignment_id>", methods=["GET", "POST"])
def edit_assignment(assignment_id):
    """Edit an existing assignment"""
    try:
        oid = ObjectId(assignment_id)
    except Exception:
        flash("Invalid assignment ID", "error")
        return redirect(url_for("index"))
    
    doc = col.find_one({"_id": oid})
    if not doc:
        flash("Assignment not found", "error")
        return redirect(url_for("index"))
    
    if request.method == "POST":
        try:
            # If priority is not provided, default to 2
            priority_str = request.form.get("priority", "").strip()
            priority = int(priority_str) if priority_str else 2
            
            assignment_data = AssignmentUpdate(
                title=request.form.get("title", ""),
                course=request.form.get("course", ""),
                notes=request.form.get("notes", ""),
                due_date=date.fromisoformat(request.form.get("due_date", "")),
                priority=priority
            )
            
            update_doc = assignment_update_to_dict(assignment_data)
            col.update_one({"_id": oid}, {"$set": update_doc})
            
            flash("Assignment updated successfully!", "success")
            return redirect(url_for("index"))
            
        except ValueError as e:
            flash(f"Error: Invalid date format - {str(e)}", "error")
            assignment = serialize_assignment(doc)
            return render_template("edit_assignment.html", assignment=assignment), 400
        except ValidationError as e:
            errors = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
            flash(f"Validation error: {errors}", "error")
            assignment = serialize_assignment(doc)
            return render_template("edit_assignment.html", assignment=assignment), 400
    
    # GET request: show edit form
    assignment = serialize_assignment(doc)
    return render_template("edit_assignment.html", assignment=assignment)


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 10000)))