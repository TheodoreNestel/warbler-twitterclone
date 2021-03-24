"""SQLAlchemy models for Warbler."""

from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()


class Follows(db.Model):
    """Connection of a follower <-> followed_user."""

    __tablename__ = 'follows'
#two primary foreign key that are the same but why?
#simple. TO keep track of both the users that follow and the ones being followed 
#this is done so that there can be overlap as in a person can be followed and follow the same user
    user_being_followed_id = db.Column( 
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True,
    )

    user_following_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True,
    )


class Likes(db.Model):
    """Mapping user likes to warbles."""

    __tablename__ = 'likes' 
    #a unique key to keep track of likes and who liked what for easy unlike / like count
    id = db.Column(
        db.Integer,
        primary_key=True
        #im adding auto increment because that seems like it needs to be here as I see no other id being passed in anywhere
        ,autoincrement=True
    )
    #the like needs to know who gave the like 
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade')
    )
    #it also needs to know which messaged its liking 
    message_id = db.Column(
        db.Integer,
        db.ForeignKey('messages.id', ondelete='cascade'),
        unique=True
    )
#on delete just makes it so the value its attached to dissappeares so will it and it wont cause errors 

class User(db.Model):
    """User in the system."""

    __tablename__ = 'users'
    #each user needs to be unique so they can easily be found in our system 
    id = db.Column(
        db.Integer,
        primary_key=True,
         #im adding auto increment because that seems like it needs to be here as I see no other id being passed in anywhere
        autoincrement=True
    )
    #this is stored for log in purposes in actuality this is just to make sure accounts arent using the same email
    #also can be used for real apps in this case so far I think its just attached to our log in process 
    email = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )
    #this value is stored so we can use to check against login attempts in the future 
    #this will also be displayed as the user's username for publicly seen stuff on our platform 
    username = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )
######################## Both are given a base image to show incase the user's doesnt work or they dont set one up 
    #users are offered the option to give us links to images to display on their profile this is stored here 
    image_url = db.Column( #this is the pfp
        db.Text,
        default="/static/images/default-pic.png",
    )
    #similar stuff as above 
    header_image_url = db.Column(
        db.Text,
        default="/static/images/warbler-hero.jpg"
    )
#########################

    #the user's bio this will be displayed on their profile page but needs to stored somewhere ;)
    bio = db.Column(
        db.Text,
    )
    #more user info
    location = db.Column(
        db.Text,
    )
    #this is where we will be storing the hashed password we got from the user 
    password = db.Column(
        db.Text,
        nullable=False,
    )
    #a relationship with messages so that we may call User.messages to get all the messages attached to a user
    messages = db.relationship('Message')

    #this relationship is used to connect followers to a user so connect user to user through follows which contains the follow 
    #information and then also join the two tables 
    followers = db.relationship(
        "User",
        secondary="follows",
        primaryjoin=(Follows.user_being_followed_id == id),
        secondaryjoin=(Follows.user_following_id == id)
    )
    #same thing as above but in the oposite direction who do you follow based on the data stored in the 'follows' table 
    following = db.relationship(
        "User",
        secondary="follows",
        primaryjoin=(Follows.user_following_id == id),
        secondaryjoin=(Follows.user_being_followed_id == id)
    )
    #similar as the follow logic but joins on table not needed again what messages do you like based on the info in 'likes' table 
    likes = db.relationship(
        'Message',
        secondary="likes"
    )
    #a function that will return info on the object 
    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"

    #a method used to check if a specified user is following this user so imagine insta "this user follows you" 
    def is_followed_by(self, other_user):
        """Is this user followed by `other_user`?"""

        found_user_list = [user for user in self.followers if user == other_user]
        return len(found_user_list) == 1

    #similar as above checks to see if you are following a particular user 
    def is_following(self, other_user):
        """Is this user following `other_use`?"""

        found_user_list = [user for user in self.following if user == other_user]
        return len(found_user_list) == 1

    @classmethod
    def signup(cls, username, email, password, image_url): # a method for signing up users wowow
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8') #we grab their password input and hash it 

        user = User( #then we grab the info passed in and slap it into a new User object 
            username=username,
            email=email,
            password=hashed_pwd,
            image_url=image_url, 
        )

        db.session.add(user) #add if to our db.session
        return user #then we return the user back to app.py 

    @classmethod
    #wowow the bigbois this is the method used to let a user into their account if they provide the correct login details
    def authenticate(cls, username, password): #it takes in the class its in username and then a password 
        """Find user with `username` and `password`.

        This is a class method (call it on the class, not an individual user.) #this is important you call this on class since 
        #we dont know who we're login in yet 
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If can't find matching user (or if password is wrong), returns False.
        """

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False


class Message(db.Model): #this class will be similar in function to our tweet one from stupid twitter 
    """An individual message ("warble")."""

    __tablename__ = 'messages'

    id = db.Column(
        db.Integer,
        primary_key=True,
         #im adding auto increment because that seems like it needs to be here as I see no other id being passed in anywhere
        autoincrement=True
    )
    #the warble or tweet NOTE: I wouldve called them twotes but ...
    #anyways they cant be empty and can only be 140 chars 
    text = db.Column(
        db.String(140),
        nullable=False,
    )
    #this is used to grab the date and will be slapped on the warble 
    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow(),
    )
    #we need to know who the fuck warbled this crap so gimme a unique primary key senapi 
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    #and well a relationship so we know whichh user warbled 
    user = db.relationship('User')

#the basic code that lets us connect to the db 
def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    db.app = app
    db.init_app(app)
