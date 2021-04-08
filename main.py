import datetime
import random, string

from flask import Flask, render_template, g, request, session, flash, redirect, url_for
from datetime import datetime, timezone
from google.cloud import datastore, storage

datastore_client = datastore.Client()
client = storage.Client()
profiles_bucket = client.get_bucket('s3717379_assign1_profilepictures')
posts_bucket = client.get_bucket('s3717379_assign1_postedpictures')

app = Flask(__name__)
app.secret_key = "3717379"

def store_users(ID, user, password, profileURL):
    entity = datastore.Entity(key=datastore_client.key('user', ID))
    entity.update({
        'id': ID,
        'userName': user,
        'password': password,
        'URL': profileURL
    })

    datastore_client.put(entity)

def store_post(user, subject, message, imageURL):
    query = datastore_client.query(kind='post')
    uniqueKey = 1
    query.order = ["-postID"]
    result = list(query.fetch(1))
    timezone_aware_dt = datetime.now(timezone.utc).strftime('%H:%M:%S %d-%m-%Y')
    
    if len(result) > 0:
        uniqueKey = result[0]["postID"] + 1 

    entity = datastore.Entity(key=datastore_client.key('post', uniqueKey))
    entity.update({
        'postID': uniqueKey,
        'userID': user,
        'subject': subject,
        'message': message,
        'imageURL': imageURL,
        'date': timezone_aware_dt
    })

    datastore_client.put(entity)

def check_userName(username):
    query = datastore_client.query(kind='user')
    query.add_filter("userName", '=', username)
    result = list(query.fetch())
    return len(result) > 0

def check_id(ID):
    query = datastore_client.query(kind='user')
    query.add_filter("id", '=', ID)
    result = list(query.fetch())
    return len(result) > 0

def fetch_id(ID):
    query = datastore_client.query(kind='user')
    query.add_filter("id", '=', ID)
    return list(query.fetch())

def store_profileimage(img):
    profiles_bucket.blob(img.name).upload_from_file(img)

def read_profileimage_path(image):
    for blob in profiles_bucket.list_blobs(): 
        if blob.name == image.name:
            return blob.public_url

def read_postimage_path(image):
    for blob in posts_bucket.list_blobs(): 
        if blob.name == image.name:
            return blob.public_url

def store_postimage(img):
    posts_bucket.blob(img.name).upload_from_file(img)

def fetch_posts(limit):
    query = datastore_client.query(kind='post')
    query.order = ['-date']

    posts = query.fetch(limit=limit)

    return posts

def fetch_userPosts(userID):
    query = datastore_client.query(kind='post')
    query.add_filter("userID", '=', userID)

    posts = list(query.fetch())

    return posts

def check_userPassword(userID, password):
    query = datastore_client.query(kind='user')
    query.add_filter("id", '=', userID)
    user = list(query.fetch(1))
    return user[0]["password"] == password

def change_userPassword(userID, password):
    key = datastore_client.key('user', userID)
    task = datastore_client.get(key)
    task['password'] = password
    datastore_client.put(task)

def fetch_postDetails(postID):
    #query = datastore_client.query(kind='post')
    #result = list(query.fetch())
    #return list(filter(lambda p: p["postID"] == postID, result))
    #return result
    print(postID)
    key = datastore_client.key("post", postID)
    task = datastore_client.get(key)
    return task

@app.route('/')
def root():
    if session.get('user') == None:
        return redirect(url_for('login'))  

    g.user = session['user']
    posts = fetch_posts(10)

    return render_template(
        'index.html', posts=posts)

@app.route('/profile')
def profile():
    g.user = session['user']

    posts = fetch_userPosts(g.user['userName'])
    return render_template(
        'profile.html', posts=posts)

@app.route('/login', methods=('GET', 'POST'))
def login():
    session.pop('_flashes', None)
    error = None

    if request.method =='POST':
        user_id = request.form['idInput']
        password = request.form['passwordInput']
        user = None

        if not check_id(user_id): 
            error = "User Doesn't Exist"
        else: 
            user = fetch_id(user_id)[0]
        
        if not user is None and not user['password'] == password:
            error = "Password is Incorrect"

        if error is None:
            session.clear()
            session['user'] = user
            g.user = user
            return redirect(url_for('root'))        
        flash(error)
    return render_template('login.html')

@app.route('/logout', methods=('GET', 'POST'))
def logout():
    session.pop('_flashes', None)
    session.pop('user', None)
    session.clear()
    g.user = None
    return redirect(url_for('root')) 

@app.route('/register', methods=('GET', 'POST'))
def register():
    session.pop('_flashes', None)
    error = None

    if request.method == 'POST':
        user_id = request.form['idInput']
        username = request.form['userInput']
        password = request.form['passwordInput']
        image = request.files['image']
        
        if check_userName(username):
            error = "Username Already Exists"
        elif check_id(user_id):
            error = "ID Already Exists"

        if error is None:
            image.name = username + ".png"
            store_profileimage(image)
            store_users(user_id, username, password, read_profileimage_path(image))
            return redirect(url_for('login'))
        flash(error)

    return render_template('register.html')

@app.route('/makepost', methods=('GET', 'POST'))
def makepost():
    g.user = session['user']

    if request.method == 'POST':
        subject = request.form['subject']
        message = request.form['message']
        image = request.files['image']
        imagepath = ""

        if image:
            image.name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(9)) + ".png"
            store_postimage(image)
            imagepath = read_postimage_path(image)
        
        store_post(g.user['userName'], subject, message, imagepath)
        return redirect(url_for('root'))
        

    return render_template(
        'index.html')
    
@app.route('/changePassword', methods=('GET', 'POST'))
def changePassword():
    g.user = session['user']
    error = None

    if request.method == 'POST':
        oldPassword = request.form['oldPassword']
        newPassword = request.form['newPassword']

        if not check_userPassword(g.user['id'], oldPassword):
            error = "Old Password is incorrect"

        if error is None:
            change_userPassword(g.user['id'], newPassword)
            return redirect(url_for('root'))
        flash(error)
        

    return render_template(
        'index.html')

@app.route('/edit')
def edit():
    g.user = session['user']

    postID = request.args.get('pid')
    post = fetch_postDetails(postID)
    print(post)
    return render_template(
        'edit.html', post=post)




if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.

    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)