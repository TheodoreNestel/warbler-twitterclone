import os

from flask import Flask, render_template, request, flash, redirect, session, g #g is just a container to hold things temporarily
#to prevent errors if the value we're looking for that we would store in g doesnt exist yet 
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm,UserDetailForm
from models import Likes, db, connect_db, User, Message

CURR_USER_KEY = "curr_user" #this is the value our session will hold to see if a user is logged in or not
#it starts with a dummy value as to not break our code that relies on the token existing

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgres:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret") #pls change this if this goes into prod
toolbar = DebugToolbarExtension(app)

connect_db(app)


##############################################################################
# User signup/login/logout


@app.before_request #this is a decorator that will force the function below to run before each request is made
#so if I make a get or a post add_user_to_g will run 
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY]) #we place our curr user into g if it exists in the session
        #this will also query for the User with the id stored in session and lets us store the entire user into g.user
        #MEANING WE GET INSTEAD OF JUST ITS ID WE GET THE WHOLE OBJECT AND ALL ITS METHODS 

    else:
        g.user = None #otherwise we ignore it 

    #so i get it and this is turbo clever. we use the user_id stored in session to query for the actual whole user object 
    #attached to that id and we store that to g.user so we can use all of User's functionality 
    #this function runs before each request to make sure sessions still has the correct id and if it doesnt then we
    #remove the User object out of g.user so this is for ease of access rather than authentication we still use
    #sessions to make sure the correct user is logged in as soon as the user_id is no longer in sessions we lose access
    #to the User object thanks to this function 
    

def do_login(user):
    """Log in user."""

    #when this function is called log in the user 

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""
    #when this function is called log out the user 
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"]) #TODO add functionality to add bio loc and pic 
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit(): #WTForm are op we've done this a million time 
        try:
            user = User.signup( # we McGrab the McInformation out of the McWTForm and slap it into our signup function we 
            #declared in models.py 
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit() #the function adds it to our db.session for us so we can just comit here 

        except IntegrityError: #all our username have to be unique so if our db yells at us run this instead 
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form) #if it fails send the user back to the form 

        do_login(user) #after we sign them up we can also log them in with the now valid log in creds 

        return redirect("/") #then send them back to the home page 

    else:
        return render_template('users/signup.html', form=form) #if no form is sent then serve them the form 


@app.route('/login', methods=["GET", "POST"]) #the route we will need to log our user in 
def login():
    """Handle user login."""

    form = LoginForm() #we instanciate our form 

    if form.validate_on_submit(): #ahhhhh? ;)
        user = User.authenticate(form.username.data,
                                 form.password.data) #this one is another function on User we pass in data from app 
                                 #then authenticate will either return the user if it finds a match or False 

        if user: #if it does pass in a User then send them back to the homepage after we add them to g.user 
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger') #if it fails we flash them a message telling them no 

    return render_template('users/login.html', form=form) #if neither then send them the form they need to log in 


@app.route('/logout')
def logout(): #
    """Handle logout of user."""
    
    
    session.pop(CURR_USER_KEY) #if they click the log out button they come to this route where we then pop the curr_user_key session cookie
    flash("Goodbye!", "info") #we tell the user bye 
    return redirect('/')
    

##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q') #if you pass in a username as a query string it will return the user you searched for 

    if not search: #if we didnt specify a user then get all of them 
        users = User.query.all() 
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all() #if we did search return taht particular user 

    return render_template('users/index.html', users=users)#then either way render either one user or all of them on this template


@app.route('/users/<int:user_id>') #shows the user's page by using anchortags
def users_show(user_id): #from the anchor tag we get a user_id
    """Show user profile."""

    user = User.query.get_or_404(user_id) #find that user or give me a 404 

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all()) #filter the messages the user wrote and sorts them by descending order 
    return render_template('users/show.html', user=user, messages=messages) #then show the template users being the folder its in
    #this is done because the user folder uses a different base template to extend from  


@app.route('/users/<int:user_id>/following')
def show_following(user_id): #once again a user_id is passed in from our html 
    """Show list of people this user is following."""

    if not g.user: #you have to be logged in to see this if not logged in then bam back to home 
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id) #we look up the user_id that was passed in 
    return render_template('users/following.html', user=user) #we load an html that grabs all the followed users


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    #this function does the same thing as above but based on the user's followers 
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)



################################################################
@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id): #this function lets a logged in user follow another user 
    """Add a follow for the currently-logged-in user."""

    if not g.user: #if we arent loged in well you cant do that so bye back to home 
        flash("Access unauthorized.", "danger")
        return redirect("/")

#**Don explain 
    followed_user = User.query.get_or_404(follow_id) #grab the id of the user we want to follow 
    g.user.following.append(followed_user)#add that id to our follows table using the relationship in User
    db.session.commit() #add it to our db 
    #this will add both the user who is following and the user getting followed to our follows table 
    #this is where the extra joins at the bottom come into play those dictate the data going into follows 
    #** Don 

    #this works because we are appending from g.user which the logged in user so the system will know that the id of the user
    #following so we just need to append the id of the user being followed 

    #the same logic but backwards is what lets us unfollow below 

    return redirect(f"/users/{g.user.id}/following") #then redirect to the follow page 


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id): #this route uses the same logic as above but to remove followers 
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")

################################################################


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = UserDetailForm()

    if form.validate_on_submit():
        password = form.password.data
        user = User.authenticate(g.user.username, password)
        bio = form.bio.data
        loc = form.loc.data
        backimg = form.backimg.data
        pfp = form.pfp.data
        email = form.email.data
        new_username = form.new_username.data
        if user :
            user.bio = bio
            user.location = loc
            user.header_image_url = backimg
            user.username = new_username
            user.email = email
            user.image_url = pfp

            db.session.add(user)
            db.session.commit()
            return redirect(f"/users/{g.user.id}")
        else: 
            flash("Access unauthorized.", "danger")
        return redirect("/")
    else : 
        return render_template("users/edit.html",form=form)
        

        

 

    
    


@app.route('/users/delete', methods=["POST"])
def delete_user(): #removes a user from our system 
    """Delete user."""

    if not g.user: #can only be deleted by the owner of the User 
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout() #log them out 

    db.session.delete(g.user) #remove them from our db 
    db.session.commit()

    return redirect("/signup") #send them back to sign in 


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm() #instanciates our message form 

    if form.validate_on_submit():
        msg = Message(text=form.text.data) #McGrab the McData and McPutIt into an Object 
        g.user.messages.append(msg) #append the new message object to user.messages using the relationship in models.py 
        db.session.commit()#commit the changes to our database 

        return redirect(f"/users/{g.user.id}") #back to the user's page now with the new message 

    return render_template('messages/new.html', form=form) #if no form is sent then present form 


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id): #if I click on the message then it gets its own html page where I can delete it 
    """Show a message."""

    msg = Message.query.get(message_id) #query for the right message with its unique id 
    return render_template('messages/show.html', message=msg) #load up an html with that message 


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id): #this route is to delete a message 
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get(message_id) #query for the message object 
    db.session.delete(msg) #McDelete it
    db.session.commit() #Commit the change 

    return redirect(f"/users/{g.user.id}") #send the user back to his timeline/page / whatever 


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """
    user = User.query.get_or_404(g.user.id)

    
    if g.user: #**Don

        following_ids = [f.id for f in g.user.following] + [g.user.id] #this here grabs all the id of people you follow
        #and puts them in a list and then adds your id on top so you can see your messages as well

        messages = (Message.query.filter(Message.user_id.in_(following_ids)).order_by(Message.timestamp.desc()).limit(100).all())
        #then here we check through all messsages using .in_ to see if they have any of our following id if they do we want them
                    

        return render_template('home.html', messages=messages) #render that home template brooooo 

    else:
        return render_template('home-anon.html') #otherwise send them to the unlogged in user homepage





#############################
#like routes 



@app.route('/users/add_like/<int:message_id>', methods=["POST"])
def add_like(message_id):

    #for this to work we need to create a new like which needs two pieces 
    #the id for the message being liked and who liked it 
    #we then will rely on relationships to grab the author based on the message id 


    #TODO add logic for unliking a tweet 


    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")


    msg = Message.query.get_or_404(message_id) #we grab the message that was liked to make sure it exists 
    
    user_id = g.user.id #we dont need this but helps my brain understand whats going on
    user = User.query.get_or_404(g.user.id) 
    try:
        new_like = Likes(user_id=user_id,message_id=message_id) #to create the new like need g.user's id and also the id of the message they like which 
    #we grabbed using the like button 
        db.session.add(new_like)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()

        liked_messages = [m.id for m in user.likes]

        delete_warble = Likes.query.filter(Likes.message_id == message_id)
        db.session.delete(delete_warble)
        db.session.commit()
        return redirect(f"/users/{g.user.id}/Likes")
        

    
    
    return  redirect(f"/users/{g.user.id}/Likes")


@app.route('/users/<int:user_id>/Likes') 
def show_warbles(user_id):

    

    user = User.query.get_or_404(user_id) #we need to grab the User object based on the id to get the logic below to work 
    users = User.query.all()

    likes_messages_id = [m.id for m in user.likes] #grabs all the message id that are liked by g.user

    liked_messsages = Message.query.filter(Message.id.in_(likes_messages_id)).order_by(Message.id.desc()).all()

    
    return render_template("users/show_warbles.html", messages=liked_messsages , users=users,user=user) #TODO make the template pretty 


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request #is run after each request 
def add_header(req):
    """Add non-caching headers on every request.""" #**Don 

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req



