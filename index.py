from flask import Flask,render_template,redirect,url_for,request,session,flash
from flask_mysqldb import MySQL
import MySQLdb
import re
import json
import firebase_admin
from firebase_admin import credentials, initialize_app, storage,firestore
import cv2

'''
1.get() -> retrieve document from firestore and returns array of dict
2. add() -> add new doc with auto gneated id in collection
3. set() -> add or replace existing one(doc) in collection
4. delete() -> delete a doc
5. update() ->update a particular data inside doc
db.collection("col_name").document(doc_id).update({"name":"fk"})
6. order_by(col_name)
7. limit(10)
8. where(three args) -> filter the doc based on condition
9. document() -> refers the particular document 
'''

cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred, {'storageBucket': 'fir-a6480.appspot.com'})
db = firestore.client()

app=Flask(__name__)
app.secret_key="123"

@app.route("/", methods=['GET', 'POST'])
def register_page():
    if request.method == "POST":
        name = request.form['name']
        mail = request.form['mail']
        phone = int(request.form['phone'])
        password = request.form['password']
        religion = request.form['religion']
        caste = request.form['caste']
        salary = int(request.form['salary'])
        age = int(request.form['age'])
        gender = request.form['gender']
        
        users_ref = db.collection('login')
        query = users_ref.where('mail', '==', mail).stream()

        #stream -execute query and return stream of doc and iterates doc one by one
        
        account = None
        for doc in query:
            account = doc.to_dict()
        
        if account:
            msg = "Account already exists"
            flash(msg, category="danger")
            return redirect(url_for("register_page"))
        else:
            users_ref.add({
                'name': name,
                'mail': mail,
                'gender': gender,
                'phone': phone,
                'password': password,
                'religion': religion,
                'caste': caste,
                'salary': salary,
                'age': age
            })
            msg = "Account successfully created"
            flash(msg, category="success")
            return redirect(url_for('profile1'))
    return render_template("mat_registration.html")

@app.route("/login", methods=['GET', 'POST'])
def login_page():
    if request.method == "POST" and 'mail' in request.form and 'password' in request.form:
        mail = request.form['mail']
        password = request.form['password']
        
        users_ref = db.collection('login')
        query = users_ref.where('mail', '==', mail).where('password', '==', password).stream()
        account = None
        user_id = None
        for doc in query:
            print(doc.to_dict())
            account = doc.to_dict()
            user_id = doc.id
        
        if account:
            session['username'] = account['name']
            session['id'] = user_id
            session['gender'] = account['gender']
            session['mail'] = account['mail']
            session['phone'] = account['phone']
            ref=db.collection("profile").where("Email","==",mail).stream()
            for doc in ref:
                d=doc.to_dict()
                session['img']=d['img']
                print(d)
            session['loggedin'] = True

            data = {"name": session['username'], "mail": account['mail'], "phone": account['phone'], "id": user_id,"img":session['img']}
            msg = f"Logged in successfully as {session['username']} and id is {session['id']}"
            flash(msg, category="success")
            return render_template("mat_profile.html", msg=msg, data=data)
        else:
            msg = "Account does not exist"
            flash(msg, category="danger")
            return render_template("mat_login.html", msg=msg)
    return render_template("mat_login.html")

@app.route("/profile", methods=['GET', 'POST'])
def profile():
    if 'loggedin' in session:
        data = {"name": session['username'], "mail": session['mail'], "phone": session['phone'], "id": session['id']}
        return render_template("mat_profile.html", data=data)
    else:
        return render_template("mat_login.html")

@app.route("/profile1", methods=["GET", "POST"])
def profile1():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        contact = request.form.get('phone')
        address = request.form.get("address")
        family = request.form.get("family")
        qualify = request.form.get('education')
        salary = request.form.get("salary")
        religion = request.form.get("religion")
        user_ref = db.collection('profile').add({
            'Name': name,
            'Email': email,
            'Contact': contact,
            'Address': address,
            'Family': family,
            'Qualify': qualify,
            'Salary': salary,
            'Religion': religion
        })
        #returns (write resut(0th index),document_ref(1st index))
        user_id = user_ref[1].id
        session['username'] = name
        session['id'] = user_id
        session['mail'] = email
        session['phone'] = contact
        session['loggedin'] = True
        video = request.files["video"]
        user_id = session["id"]
        
        # Short Video about user
        bucket = storage.bucket()
        blob = bucket.blob(f"videos/{user_id}.mp4")
        blob.upload_from_file(video)
        blob.make_public()
        video_url = blob.public_url
        
        # Update user profile in Firestore with video URL
        db.collection("profile").document(user_id).update({"video_url": video_url})

        flash("Video uploaded successfully", category="success")
        cam = cv2.VideoCapture(0)
        while True:
            ret, frame = cam.read()
            cv2.imshow("Face Image", frame)
            if cv2.waitKey(100) & 0xFF == ord("q"):
                break
            cv2.imwrite(f"{name}.png", frame)
        cam.release()
        cv2.destroyAllWindows()
        
        fileName = f"{name}.png"
        bucket = storage.bucket()       #create a ref to storage bucket
        blob = bucket.blob(f"images/{fileName}")   
        #create ref to blob(object) in stoarge bucket specify path in bucket where to upload 
        blob.upload_from_filename(fileName) #takes file from local path to bucket 
        blob.make_public()   #makes upload blob publicy accessible
        db.collection("profile").document(user_id).update({"img":blob.public_url})
        session['profile_data'] = {"name": name, "mail": email, "phone": contact, "id": user_id,"img":blob.public_url}
        return render_template("mat_profile.html",data=session['profile_data'])
    return render_template("mat_profile2.html")

@app.route("/logout",methods=['GET','POST'])

def logout_page():
     if 'loggedin' in session:
        session.pop('loggedin',None)
        session.pop('username',None)
        session.pop('gender',None)
        session.pop('id',None)
     return redirect(url_for('login_page'))

@app.route("/preference", methods=['GET', 'POST'])
def preference_page():
    data = []
    if request.method == "POST" and 'loggedin' in session and request.form['age'] != "" and request.form['caste'] != "" and request.form['religion'] != "":
        age = int(request.form['age'])
        user_id = session['id']
        caste = request.form['caste']
        religion = request.form['religion']

        # Add preference to Firestore
        db.collection('preference').add({
            'age': age,
            'user_id': user_id,
            'caste': caste,
            'religion': religion
        })

        # Reference to the users collection
        users_ref = db.collection('login')

        # Query to get users by age and caste separately
        query_age = users_ref.where("age", "==", age).stream()
        query_caste = users_ref.where("caste", "==", caste).stream()

        # Combine the results from both queries
        results = list(query_age) + list(query_caste)

        # Optionally remove duplicates if needed (based on document ID)
        results = list({doc.id: doc for doc in results}.values())
        data=[]
        for doc in results:
            if doc.id!=session['id']:
                data.append(doc.to_dict())
        return render_template("mat_preference.html", data=data, name=session['username'], mail=session['mail'])

    elif 'loggedin' in session:
        return render_template("mat_preference.html", name=session['username'], mail=session['mail'])

    return render_template("mat_login.html")


@app.route("/update_profile", methods=['GET', 'POST'])
def update_profile_page():
    if request.method == "POST" and 'loggedin' in session:
        user_ref = db.collection('login').document(session['id']) #reference to documentn with session['id'] in db
        user_doc = user_ref.get()   #The get() method retrieves a single snapshot of the document from the Firestore database.
        
        if user_doc.exists:
            data = user_doc.to_dict()
            name = request.form['name']
            mail = request.form['mail']
            caste = request.form['caste']
            religion = request.form['religion']
            salary = request.form['salary']
            age = request.form['age']
            phone = request.form['phone']

            user_ref.update({
                'name': name,
                'caste': caste,
                'religion': religion,
                'salary': salary,
                'age': age,
                'phoneno': phone,
                'mail': mail
            })
        # Fetch the document(s) matching the query
        ref = db.collection("profile").where("Email", "==", session['mail'])
        d = ref.get()

        # Check if any documents were found
        if d:
            for doc in d:
                # Get the document reference
                doc_ref = db.collection("profile").document(doc.id)
                # Update the document
                doc_ref.update({
                    'Name': name,
                    'Caste': caste,
                    'Religion': religion,
                    'Salary': salary,
                    'age': age,
                    'Contact': phone,
                    'Email': mail
                })
                msg = "Account successfully updated"
                flash(msg, category="success")
                return render_template("mat_login.html", data=data)
    elif 'loggedin' in session:
        user_ref = db.collection('login').document(session['id'])
        user_doc = user_ref.get()

        if user_doc.exists:
            data = user_doc.to_dict()
            print(data)
            data['img']=session['img']
            return render_template("mat_profile1.html", data=data, id=session['id'])
    msg = "Account not logged in"
    flash(msg, category="danger")
    return render_template("mat_login.html")

@app.route("/payment", methods=['GET', 'POST'])
def payment_page():
    if request.method == "POST":
        package = "gold" if request.form['gold'] != "" else "assisted"
        pay_type = request.form['payment']
        amount = int(request.form['gold'] if package == "gold" else request.form['assisted'])
        user_id = session['id']
        date = firestore.SERVER_TIMESTAMP

        # Add payment to Firestore
        db.collection('payment').add({
            'user_id': user_id,
            'package': package,
            'amount': amount,
            'date': date,
            'pay_type': pay_type
        })

        msg = "Payment successfully completed"
        flash(msg, category="success")
        return render_template("mat_payment.html", name=session['username'])
    
    return render_template("mat_payment.html", name=session['username'], mail=session['mail'])

@app.route("/transaction")
def transaction_page():
    user_id = session['id']
    transactions = db.collection('payment').where('user_id', '==', user_id).stream()
    data = [doc.to_dict() for doc in transactions]

    return render_template("mat_transaction.html", data=data)

@app.route("/submit_feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        name = request.form["name"]
        rating = int(request.form["rating"])
        text = request.form["review"]
        db.collection('Feedback').add({
            'Name': session['username'],
            'Comment': text,
            'Rating': rating,
            'mail':session['mail']
        })
        return render_template("feedback.html")
    return render_template("feedback.html")
@app.route("/all_profile", methods=["GET", "POST"])
def all_profile():
    profile_ref=db.collection("profile").stream()
    data=[]
    for doc in profile_ref:
        data.append(doc.to_dict())
    print(data)
    return render_template("card.html", data=data)


@app.route("/admin_login", methods=['GET', 'POST'])
def admin_login():
    if request.method == "POST" and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']

        # Assuming admin credentials are stored in Firestore
        admin_ref = db.collection('admin').where('username', '==', username).where('password', '==', password).stream()
        admin = None
        for doc in admin_ref:
            admin = doc.to_dict()

        if admin:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash("Admin login successful", category="success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid credentials", category="danger")
    return render_template("admin_login.html")


@app.route("/admin_dashboard")
def admin_dashboard():
    if 'admin_logged_in' in session:
        # Fetch some basic statistics
        total_users = len([doc for doc in db.collection('login').stream()])
        total_profiles = len([doc for doc in db.collection('profile').stream()])
        total_payments = len([doc for doc in db.collection('payment').stream()])

        stats = {
            'total_users': total_users,
            'total_profiles': total_profiles,
            'total_payments': total_payments
        }

        return render_template("admin_dashboard.html", stats=stats)
    else:
        flash("Please log in as an admin first", category="danger")
        return redirect(url_for("admin_login"))

@app.route("/admin_users")
def admin_users():
    if 'admin_logged_in' in session:
        users = [doc.to_dict() for doc in db.collection('login').stream()]
        print(users)
        return render_template("user_manage.html", users=users)
    else:
        flash("Please log in as an admin first", category="danger")
        return redirect(url_for("admin_login"))

@app.route("/delete_user/<string:user_id>")
def delete_user(user_id):
    if 'admin_logged_in' in session:
        db.collection("login").document(user_id).delete()
        flash("user deleted successfully",category='danger')
        return render_template("manage_user.html")
    else:
        return render_template("admin_login.html")

@app.route('/success_stories')
def success_stories():
    feedback_ref = db.collection('Feedback')
    feedback_docs = feedback_ref.stream()

    feedback_list = []
    for doc in feedback_docs:
        d = doc.to_dict()
        user_docs = db.collection("profile").where("Email", "==", d['mail']).get()

        # Since 'get()' returns a list of documents, we need to iterate or pick the first document
        if user_docs:
            print(user_docs[0].to_dict())
            user_ref = user_docs[0].to_dict()  
            d['video'] = user_ref.get('video_url', '')  # Use .get() to avoid KeyError if 'video_url' doesn't exist
            d['img']=user_ref.get("img","")
        feedback_list.append(d)

    return render_template('success_stories.html', reviews=feedback_list)

@app.route('/create_album', methods=['GET', 'POST'])
def create_album():
    if request.method == 'POST':
        album_name = request.form['album_name']
        description = request.form['description']
        photo=request.files['photo']
        author_id = session['id']
        bucket=storage.bucket()
        blob=bucket.blob(f"photos/{author_id}-{album_name}/{photo.filename}")
        blob.upload_from_file(photo)
        blob.make_public()
        db.collection('albums').add({
            'album_name': album_name,
            'description': description,
            'author_id': author_id,
            'date': firestore.SERVER_TIMESTAMP,
            'img':blob.public_url
        })
        flash("Album created successfully!", category="success")
        return render_template("upload_photo.html")
    return render_template('create_album.html')

@app.route("/view_album",methods=['GET','POST'])

def view_album():
    data={}
    album_ref=db.collection("albums").where("author_id","==",session['id']).get()
    if album_ref:
        for doc in album_ref:
            data[doc.id]=doc.to_dict()
    return render_template("view_album.html",data=data)

@app.route('/upload_photo/<string:photo_id>/<string:photo_name>', methods=['GET', 'POST'])
def upload_photo(photo_id,photo_name):
    if request.method == 'POST':
        photo = request.files['photo']
        description = request.form['description']
        user_id = session['id']
        
        bucket = storage.bucket()
        blob = bucket.blob(f"photos/{user_id}-{photo_id}-{photo.filename}")
        blob.upload_from_file(photo)
        blob.make_public()
        photo_url = blob.public_url

        # Query the album document with the specific album_id
        album_ref = db.collection('albums').where('author_id', '==', session['id']).get()

        # Check if album exists
        if album_ref:
            # Add photo information to the photos sub-collection of the matching album
            for album_doc in album_ref:
                db.collection('albums').document(album_doc.id).collection('photos').add({
                    'photo_url': photo_url,
                    'description': description,
                    'upload_date': firestore.SERVER_TIMESTAMP
                })

            flash("Photo uploaded successfully!", category="success")
        else:
            flash("Album not found!", category="error")

        return redirect(url_for('upload_photo',photo_id=photo_id,photo_name=photo_name))
    
    return render_template('upload_photo.html',photo_id=photo_id,photo_name=photo_name)

@app.route("/gallery/<string:photo_id>/<string:photo_name>",methods=['GET','POST'])

def gallery(photo_id,photo_name):
      ref=db.collection("albums").document(photo_id).collection("photos")
      data=ref.stream()
      images=[]
      for doc in data:
          images.append(doc.to_dict())
      return render_template("gallery.html",data=images,album_name=photo_name,album_id=photo_id)
if __name__=="__main__":
    app.run(debug=True,port=5000)