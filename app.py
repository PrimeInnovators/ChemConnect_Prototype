from flask import Flask, request, jsonify, session, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_key_for_dev') # Use environment variable for production

# MongoDB Connection
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://pravanguptaTPIN:JaiMahaKaali2006@chemconnect-cluster.aw03lpy.mongodb.net/')
client = MongoClient(MONGO_URI)
db = client.chemconnect_db # Your database name

# Collections
users_collection = db.users
requests_collection = db.requests
supplies_collection = db.supplies
contacts_collection = db.contacts

# --- Helper Functions ---
def is_logged_in():
    return 'user_id' in session

def get_current_user():
    if is_logged_in():
        user_id = session['user_id']
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        if user:
            user['id'] = str(user['_id'])          # ✅ Fix: Add this line
            user['_id'] = str(user['_id'])         # optional
            return user
    return None

# --- API Endpoints ---

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.json
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    college_name = data.get('collegeName')
    college_address = data.get('collegeAddress')
    contact_person = data.get('contactPerson')
    designation = data.get('designation')
    email = data.get('email')
    phone_number = data.get('phoneNumber')
    university_affiliation = data.get('universityAffiliation')
    password = data.get('password')
    confirm_password = data.get('confirmPassword')
    additional_info = data.get('additionalInfo')

    if not all([college_name, college_address, contact_person, designation, email, phone_number, university_affiliation, password, confirm_password]):
        return jsonify({'message': 'All required fields must be filled'}), 400

    if password != confirm_password:
        return jsonify({'message': 'Passwords do not match!'}), 400

    if len(password) < 8:
        return jsonify({'message': 'Password must be at least 8 characters long!'}), 400

    if users_collection.find_one({'email': email.lower()}):
        return jsonify({'message': 'A college with this email is already registered!'}), 409 # Conflict

    new_user = {
        'collegeName': college_name,
        'collegeAddress': college_address,
        'contactPerson': contact_person,
        'designation': designation,
        'email': email.lower(),
        'phoneNumber': phone_number,
        'universityAffiliation': university_affiliation,
        'password': password, # In a real app, hash this password!
        'additionalInfo': additional_info,
        'verified': False, # Default to false, verification process would be external
        'registeredAt': datetime.datetime.utcnow()
    }

    try:
        result = users_collection.insert_one(new_user)
        return jsonify({'message': 'Registration successful! Your college details have been submitted for verification.', 'user_id': str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.json
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Please fill in all fields.'}), 400

    user = users_collection.find_one({'email': email.lower(), 'password': password}) # Again, hash comparison in real app

    if user:
        session['user_id'] = str(user['_id'])
        # Prepare user data for frontend, excluding sensitive info like password
        user_data = {
            'id': str(user['_id']),
            'collegeName': user.get('collegeName'),
            'collegeAddress': user.get('collegeAddress'),
            'contactPerson': user.get('contactPerson'),
            'designation': user.get('designation'),
            'email': user.get('email'),
            'phoneNumber': user.get('phoneNumber'),
            'universityAffiliation': user.get('universityAffiliation'),
            'verified': user.get('verified'),
            'registeredAt': user.get('registeredAt').isoformat() if user.get('registeredAt') else None,
            'additionalInfo': user.get('additionalInfo')
        }
        return jsonify({'message': 'Login successful!', 'user': user_data}), 200
    else:
        return jsonify({'message': 'Invalid email or password. Please try again.'}), 401 # Unauthorized

@app.route('/api/logout', methods=['POST'])
def logout_user():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/request_item', methods=['POST'])
def submit_request():
    if not is_logged_in():
        return jsonify({'message': 'Unauthorized. Please log in.'}), 401

    data = request.json
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    current_user = get_current_user()
    if not current_user:
        return jsonify({'message': 'User not found.'}), 404

    # Extract data from request, ensure all required fields are present
    item_type = data.get('itemType')
    item_details = data.get('itemDetails')
    urgency = data.get('urgency')

    if not all([item_type, item_details, urgency]):
        return jsonify({'message': 'Missing required request fields.'}), 400

    new_request = {
        'userId': current_user['id'],
        'collegeName': current_user['collegeName'],
        'contactPerson': current_user['contactPerson'],
        'email': current_user['email'],
        'phone': current_user['phoneNumber'],
        'itemType': item_type,
        'itemDetails': item_details,
        'urgency': urgency,
        'timestamp': datetime.datetime.utcnow()
    }

    try:
        requests_collection.insert_one(new_request)
        return jsonify({'message': 'Request submitted successfully!'}), 201
    except Exception as e:
        return jsonify({'message': f'Failed to submit request: {str(e)}'}), 500

@app.route('/api/supply_item', methods=['POST'])
def list_supply_item():
    if not is_logged_in():
        return jsonify({'message': 'Unauthorized. Please log in.'}), 401

    data = request.json
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    current_user = get_current_user()
    if not current_user:
        return jsonify({'message': 'User not found.'}), 404

    # Extract data from request
    item_type = data.get('itemType')
    item_details = data.get('itemDetails')
    price = data.get('price')
    location = data.get('location')

    if not all([item_type, item_details, price, location]):
        return jsonify({'message': 'Missing required supply fields.'}), 400

    new_supply = {
        'userId': current_user['id'],
        'collegeName': current_user['collegeName'],
        'contactPerson': current_user['contactPerson'],
        'email': current_user['email'],
        'phone': current_user['phoneNumber'],
        'itemType': item_type,
        'itemDetails': item_details,
        'price': price,
        'location': location,
        'timestamp': datetime.datetime.utcnow()
    }

    try:
        supplies_collection.insert_one(new_supply)
        return jsonify({'message': 'Item listed for supply successfully!'}), 201
    except Exception as e:
        return jsonify({'message': f'Failed to list item: {str(e)}'}), 500

@app.route('/api/get_supplies', methods=['GET'])
def get_supplies():
    # This endpoint can be accessed by anyone for search, no login required
    # Add filtering logic here if needed based on query parameters
    query = request.args.get('query', '').lower()
    item_type = request.args.get('itemType', '').lower()

    filter_criteria = {}
    if query:
        filter_criteria['$or'] = [
            {'itemDetails': {'$regex': query, '$options': 'i'}},
            {'collegeName': {'$regex': query, '$options': 'i'}},
            {'location': {'$regex': query, '$options': 'i'}}
        ]
    if item_type:
        filter_criteria['itemType'] = item_type

    supplies = []
    for supply in supplies_collection.find(filter_criteria).sort('timestamp', -1):
        supply['_id'] = str(supply['_id'])
        supply['userId'] = str(supply['userId']) # Ensure userId is string
        supply['timestamp'] = supply['timestamp'].isoformat()
        supplies.append(supply)
    return jsonify(supplies), 200

@app.route('/api/get_my_requests', methods=['GET'])
def get_my_requests():
    if not is_logged_in():
        return jsonify({'message': 'Unauthorized. Please log in.'}), 401

    current_user = get_current_user()
    if not current_user:
        return jsonify({'message': 'User not found.'}), 404

    my_requests = []
    for req in requests_collection.find({'userId': current_user['id']}).sort('timestamp', -1):
        req['_id'] = str(req['_id'])
        req['userId'] = str(req['userId'])
        req['timestamp'] = req['timestamp'].isoformat()
        my_requests.append(req)
    return jsonify(my_requests), 200

@app.route('/api/get_my_supplies', methods=['GET'])
def get_my_supplies():
    if not is_logged_in():
        return jsonify({'message': 'Unauthorized. Please log in.'}), 401

    current_user = get_current_user()
    if not current_user:
        return jsonify({'message': 'User not found.'}), 404

    my_supplies = []
    for sup in supplies_collection.find({'userId': current_user['id']}).sort('timestamp', -1):
        sup['_id'] = str(sup['_id'])
        sup['userId'] = str(sup['userId'])
        sup['timestamp'] = sup['timestamp'].isoformat()
        my_supplies.append(sup)
    return jsonify(my_supplies), 200

@app.route('/api/contact_us', methods=['POST'])
def submit_contact_form():
    data = request.json
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    name = data.get('name')
    email = data.get('email')
    college = data.get('college')
    subject = data.get('subject')
    message = data.get('message')

    if not all([name, email, college, subject, message]):
        return jsonify({'message': 'All contact form fields are required.'}), 400

    new_contact = {
        'name': name,
        'email': email,
        'college': college,
        'subject': subject,
        'message': message,
        'timestamp': datetime.datetime.utcnow()
    }

    try:
        contacts_collection.insert_one(new_contact)
        return jsonify({'message': 'Contact form submitted successfully!'}), 201
    except Exception as e:
        return jsonify({'message': f'Failed to submit contact form: {str(e)}'}), 500

@app.route('/api/get_supplier_info/<supplier_name>', methods=['GET'])
def get_supplier_info(supplier_name):
    # First, check if the supplier is a registered user
    user_supplier = users_collection.find_one({'collegeName': supplier_name})
    if user_supplier:
        supplier_info = {
            'name': user_supplier.get('collegeName'),
            'contactPerson': user_supplier.get('contactPerson'),
            'email': user_supplier.get('email'),
            'phone': user_supplier.get('phoneNumber'),
            'address': user_supplier.get('collegeAddress', 'Not specified')
        }
        return jsonify(supplier_info), 200

    # If not a registered user, check predefined suppliers (if you still want them)
    # For this backend, we'll assume all suppliers are registered users or come from supplies collection
    # If you want to keep static predefined suppliers, you'd hardcode them here or load from a config
    # For now, we'll just return 404 if not found in users collection.
    return jsonify({'message': 'Supplier not found.'}), 404

# --- Serve Static Files (for development) ---
# In a production environment, a web server like Nginx or Apache would serve static files.
# For development, Flask can serve them.
@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def static_files(path):
    return app.send_static_file(path)

if __name__ == '__main__':
    # Initialize demo users if the collection is empty
    if users_collection.count_documents({}) == 0:
        print("Initializing demo users...")
        sample_users = [
            {
                'collegeName': "Indian Institute of Technology Delhi",
                'collegeAddress': "Hauz Khas, New Delhi, Delhi 110016",
                'contactPerson': "Dr. Sarah Johnson",
                'designation': "Head of Chemistry Department",
                'email': "chemistry@iitd.ac.in",
                'phoneNumber': "+91-9876543210",
                'universityAffiliation': "IIT Delhi (Institute of National Importance)",
                'password': "demo123",
                'additionalInfo': "Leading research institute with state-of-the-art chemistry labs",
                'verified': True,
                'registeredAt': datetime.datetime.utcnow()
            },
            {
                'collegeName': "Delhi University - Chemistry Department",
                'collegeAddress': "North Campus, Delhi University, Delhi 110007",
                'contactPerson': "Prof. Michael Chen",
                'designation': "Department Coordinator",
                'email': "chem@du.ac.in",
                'phoneNumber': "+91-9876543211",
                'universityAffiliation': "University of Delhi",
                'password': "demo456",
                'additionalInfo': "One of India's premier universities with excellent chemistry facilities",
                'verified': False,
                'registeredAt': datetime.datetime.utcnow()
            },
            {
                'collegeName': "Jamia Millia Islamia",
                'collegeAddress': "Jamia Nagar, New Delhi, Delhi 110025",
                'contactPerson': "Dr. Priya Sharma",
                'designation': "Assistant Professor",
                'email': "chem@jmi.ac.in",
                'phoneNumber': "+91-9876543212",
                'universityAffiliation': "Jamia Millia Islamia (Central University)",
                'password': "demo789",
                'additionalInfo': "Central university with modern chemistry laboratories",
                'verified': True,
                'registeredAt': datetime.datetime.utcnow()
            },
            # Predefined suppliers from your original HTML, now as users
            {
                "collegeName": "HBTU Kanpur",
                "contactPerson": "Dr. Alok Sharma",
                "email": "alok.sharma@hbtu.ac.in",
                "phoneNumber": "+919876512345",
                "collegeAddress": "Harcourt Butler Technical University, Kanpur, Uttar Pradesh 208002",
                "designation": "Professor", # Added for consistency
                "universityAffiliation": "State University", # Added for consistency
                "password": "hbtu",
                "verified": True,
                "registeredAt": datetime.datetime.utcnow()
            },
            {
                "collegeName": "IIT Kanpur",
                "contactPerson": "Prof. Ritu Singh",
                "email": "ritu.singh@iitk.ac.in",
                "phoneNumber": "+919988776655",
                "collegeAddress": "Indian Institute of Technology Kanpur, Kalyanpur, Kanpur, Uttar Pradesh 208016",
                "designation": "Professor", # Added for consistency
                "universityAffiliation": "IIT", # Added for consistency
                "password": "iitk",
                "verified": True,
                "registeredAt": datetime.datetime.utcnow()
            },
            {
                "collegeName": "PSIT Kanpur",
                "contactPerson": "Mr. Vivek Kumar",
                "email": "vivek.kumar@psit.ac.in",
                "phoneNumber": "+919123456789",
                "collegeAddress": "Pranveer Singh Institute of Technology, Bhauti, Kanpur, Uttar Pradesh 209305",
                "designation": "Lecturer", # Added for consistency
                "universityAffiliation": "Private College", # Added for consistency
                "password": "psit",
                "verified": True,
                "registeredAt": datetime.datetime.utcnow()
            }
        ]
        users_collection.insert_many(sample_users)
        print("Demo users initialized successfully.")

    # Initialize demo supplies if the collection is empty
    if supplies_collection.count_documents({}) == 0:
        print("Initializing demo supplies...")
        # Find the user IDs for the demo suppliers
        hbtu_user = users_collection.find_one({"collegeName": "HBTU Kanpur"})
        iitk_user = users_collection.find_one({"collegeName": "IIT Kanpur"})
        psit_user = users_collection.find_one({"collegeName": "PSIT Kanpur"})

        sample_supplies = []
        if hbtu_user:
            sample_supplies.append({
                "userId": hbtu_user['_id'],
                "collegeName": "HBTU Kanpur",
                "contactPerson": hbtu_user['contactPerson'],
                "email": hbtu_user['email'],
                "phone": hbtu_user['phoneNumber'],
                "itemType": "chemical",
                "itemDetails": "Sodium Hydroxide (NaOH) - 5kg, ACS Reagent Grade, unopened container",
                "price": "1200",
                "location": "Kanpur",
                "timestamp": datetime.datetime.utcnow() - datetime.timedelta(days=5)
            })
        if iitk_user:
            sample_supplies.extend([
                {
                    "userId": iitk_user['_id'],
                    "collegeName": "IIT Kanpur",
                    "contactPerson": iitk_user['contactPerson'],
                    "email": iitk_user['email'],
                    "phone": iitk_user['phoneNumber'],
                    "itemType": "equipment",
                    "itemDetails": "UV-Vis Spectrophotometer, Used but well-maintained, includes cuvette set",
                    "price": "25000",
                    "location": "Kanpur",
                    "timestamp": datetime.datetime.utcnow() - datetime.timedelta(days=10)
                },
                {
                    "userId": iitk_user['_id'],
                    "collegeName": "IIT Kanpur",
                    "contactPerson": iitk_user['contactPerson'],
                    "email": iitk_user['email'],
                    "phone": iitk_user['phoneNumber'],
                    "itemType": "equipment",
                    "itemDetails": "Transmission Electron Microscope, Used in material science, in nanotechnology. Prices due to operational charges charged on a weekly basis",
                    "price": "12000 per week",
                    "location": "Kanpur",
                    "timestamp": datetime.datetime.utcnow() - datetime.timedelta(days=15)
                }
            ])
        if psit_user:
            sample_supplies.append({
                "userId": psit_user['_id'],
                "collegeName": "PSIT Kanpur",
                "contactPerson": psit_user['contactPerson'],
                "email": psit_user['email'],
                "phone": psit_user['phoneNumber'],
                "itemType": "glassware",
                "itemDetails": "Glassware Set, Various beakers, flasks, and test tubes - 25 pieces total",
                "price": "FREE",
                "location": "Kanpur",
                "timestamp": datetime.datetime.utcnow() - datetime.timedelta(days=7)
            })
        
        if sample_supplies:
            supplies_collection.insert_many(sample_supplies)
            print("Demo supplies initialized successfully.")

    app.run(debug=True, port=5000)

