# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#
import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object("config")

db = SQLAlchemy(app)

migrate = Migrate(app, db)

# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#


class Show(db.Model):
    __tablename__ = "shows"

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.ForeignKey("venues.id"))
    artist_id = db.Column(db.ForeignKey("artists.id"))
    start_time = db.Column(db.DateTime(), nullable=False)


class Venue(db.Model):
    __tablename__ = "venues"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    genres = db.Column(db.ARRAY(db.String), nullable=False)
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.String(120))
    shows = db.relationship(
        "Show",
        backref="venue",
        cascade="all, delete-orphan",
    )


class Artist(db.Model):
    __tablename__ = "artists"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    genres = db.Column(db.ARRAY(db.String), nullable=False)
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.String(120))
    shows = db.relationship(
        "Show",
        backref="artist",
        cascade="all, delete-orphan",
    )


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format="medium"):
    date = dateutil.parser.parse(value)
    if format == "full":
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == "medium":
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale="en")


app.jinja_env.filters["datetime"] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


@app.route("/")
def index():
    return render_template("pages/home.html")


#  Venues
#  ----------------------------------------------------------------


@app.route("/venues")
def venues():
    # TODO: replace with real venues data.
    #       num_upcoming_shows should be aggregated based on number of upcoming shows per venue.
    # venues = Venue.query.order_by(Venue.state).all()
    city_and_state = Venue.query.distinct(Venue.state, Venue.city).all()
    data = []
    for city in city_and_state:
        city_details = {"state": city.state, "city": city.city}

        # Fetch Venues for each distinct city
        venues = Venue.query.filter_by(state=city.state, city=city.city).all()
        venues_data = []
        for venue in venues:
            current_time = datetime.now()
            upcoming_shows = len(
                list(filter(lambda s: s.start_time > current_time, venue.shows))
            )

            venue_dict = {
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": upcoming_shows,
            }
            venues_data.append(venue_dict)
        city_details["venues"] = venues_data
        data.append(city_details)

    return render_template("pages/venues.html", areas=data)


@app.route("/venues/<int:venue_id>")
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    venue = Venue.query.get(venue_id)

    # Upcoming Shows logic
    upcoming_shows_query = (
        db.session.query(Show)
        .join(Venue)
        .filter(Show.venue_id == venue_id)
        .filter(Show.start_time > datetime.now())
        .all()
    )
    upcoming_shows = []
    for show in upcoming_shows_query:
        details = {
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
        }
        upcoming_shows.append(details)

    # Past Shows logic
    past_shows_query = (
        db.session.query(Show)
        .join(Venue)
        .filter(Show.venue_id == venue_id)
        .filter(Show.start_time < datetime.now())
        .all()
    )
    past_shows = []
    for show in past_shows_query:
        details = {
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
        }
        past_shows.append(details)

    venue.upcoming_shows_count = len(upcoming_shows)
    venue.upcoming_shows = upcoming_shows
    venue.past_shows_count = len(past_shows)
    venue.past_shows = past_shows

    return render_template("pages/show_venue.html", venue=venue)


#  Search Venue
#  ----------------------------------------------------------------


@app.route("/venues/search", methods=["POST"])
def search_venues():
    search_term = request.form["search_term"]
    query = Venue.query.filter(Venue.name.ilike(f"%{search_term}%")).all()

    response = {"count": "", "data": []}

    response["count"] = len(query)
    for venue in query:
        venue_details = {"id": venue.id, "name": venue.name}
        response["data"].append(venue_details)

    return render_template(
        "pages/search_venues.html",
        results=response,
        search_term=request.form.get("search_term", ""),
    )


#  Create Venue
#  ----------------------------------------------------------------


@app.route("/venues/create", methods=["GET"])
def create_venue_form():
    form = VenueForm()
    return render_template("forms/new_venue.html", form=form)


@app.route("/venues/create", methods=["POST"])
def create_venue_submission():
    form = VenueForm(request.form)

    if form.validate():
        venue = Venue(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            address=form.address.data,
            phone=form.phone.data,
            genres=form.genres.data,
            facebook_link=form.facebook_link.data,
            image_link=form.image_link.data,
            seeking_talent=form.seeking_talent.data,
            seeking_description=form.seeking_description.data,
            website=form.website_link.data,
        )

        db.session.add(venue)
        db.session.commit()
        flash("Venue " + request.form["name"] + " was successfully listed!")
    else:
        db.session.rollback()

        for field, message in form.errors.items():
            flash(field + " - " + str(message), "danger")

        db.session.close()
    return render_template("pages/home.html")


#  Delete Venue
#  ----------------------------------------------------------------


@app.route("/venues/<venue_id>/delete", methods=["GET"])
def delete_venue(venue_id):
    try:
        venue = Venue.query.get(venue_id)
        db.session.delete(venue)
        db.session.commit()
        flash("Venue was successfully deleted!")
    except:
        db.session.rollback()
    finally:
        db.session.close()
    return render_template("pages/home.html")


#  Update Venue
#  ----------------------------------------------------------------


@app.route("/venues/<int:venue_id>/edit", methods=["GET"])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get(venue_id)
    form.genres.data = venue.genres.getlist("genres")
    return render_template("forms/edit_venue.html", form=form, venue=venue)


@app.route("/venues/<int:venue_id>/edit", methods=["POST"])
def edit_venue_submission(venue_id):
    form = VenueForm(request.form)
    venue = Venue.query.get(venue_id)

    if form.validate():
        venue.name = form.name.data
        venue.city = form.city.data
        venue.state = form.state.data
        venue.phone = form.phone.data
        venue.genres = form.genres.data
        venue.facebook_link = form.facebook_link.data
        venue.image_link = form.image_link.data
        venue.website = form.website_link.data
        venue.seeking_talent = form.seeking_talent.data
        venue.seeking_description = form.seeking_description.data
        db.session.add(venue)
        db.session.commit()
        flash("Venue edited successfully")
    else:
        db.session.rollback()
        for field, message in form.errors.items():
            flash(field + " - " + str(message), "danger")

        # flash(
        #     "An error occurred. Venue " + request.form["name"] + " could not be edited."
        # )
        db.session.close()
    return redirect(url_for("show_venue", venue_id=venue_id))


#  Artists
#  ----------------------------------------------------------------


@app.route("/artists")
def artists():
    data = Artist.query.all()
    return render_template("pages/artists.html", artists=data)


@app.route("/artists/<int:artist_id>")
def show_artist(artist_id):
    # shows the artist page with the given artist_id
    artist = Artist.query.get(artist_id)

    # Upcoming Shows logic
    upcoming_shows_query = (
        db.session.query(Show)
        .join(Venue)
        .filter(Show.artist_id == artist_id)
        .filter(Show.start_time > datetime.now())
        .all()
    )
    upcoming_shows = []
    for show in upcoming_shows_query:
        details = {
            "venue_id": show.venue_id,
            "venue_name": show.venue.name,
            "venue_image_link": show.venue.image_link,
            "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
        }
        upcoming_shows.append(details)

    # Past Shows logic
    past_shows_query = (
        db.session.query(Show)
        .join(Venue)
        .filter(Show.artist_id == artist_id)
        .filter(Show.start_time < datetime.now())
        .all()
    )
    past_shows = []
    for show in past_shows_query:
        details = {
            "venue_name": show.venue.name,
            "venue_id": show.venue.id,
            "venue_image_link": show.venue.image_link,
            "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
        }
        past_shows.append(details)

    artist.upcoming_shows_count = len(upcoming_shows)
    artist.upcoming_shows = upcoming_shows
    artist.past_shows_count = len(past_shows)
    artist.past_shows = past_shows
    return render_template("pages/show_artist.html", artist=artist)


#  Search Artists
#  ----------------------------------------------------------------


@app.route("/artists/search", methods=["POST"])
def search_artists():
    search_term = request.form["search_term"]
    query_results = Artist.query.filter(Artist.name.ilike(f"%{search_term}%")).all()

    response = {"count": "", "data": []}

    response["count"] = len(query_results)
    for artist in query_results:
        artist_details = {"id": artist.id, "name": artist.name}
        response["data"].append(artist_details)

    return render_template(
        "pages/search_artists.html",
        results=response,
        search_term=request.form.get("search_term", ""),
    )


#  Create Artist
#  ----------------------------------------------------------------


@app.route("/artists/create", methods=["GET"])
def create_artist_form():
    form = ArtistForm()
    return render_template("forms/new_artist.html", form=form)


@app.route("/artists/create", methods=["POST"])
def create_artist_submission():
    form = ArtistForm(request.form)
    if form.validate():
        artist = Artist(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            phone=form.phone.data,
            genres=form.genres.data,
            facebook_link=form.facebook_link.data,
            image_link=form.image_link.data,
            website=form.website_link.data,
            seeking_venue=form.seeking_venue.data,
            seeking_description=form.seeking_description.data,
        )

        db.session.add(artist)
        db.session.commit()
        flash("Artist " + request.form["name"] + " was successfully listed!")
    else:
        db.session.rollback()
        flash(
            "An error occurred. Artist "
            + request.form["name"]
            + " could not be listed."
        )
        db.session.close()
    return render_template("pages/home.html")


#  Update Artist
#  ----------------------------------------------------------------


@app.route("/artists/<int:artist_id>/edit", methods=["GET"])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)
    return render_template("forms/edit_artist.html", form=form, artist=artist)


@app.route("/artists/<int:artist_id>/edit", methods=["POST"])
def edit_artist_submission(artist_id):
    form = ArtistForm(request.form)
    artist = Artist.query.get(artist_id)

    if form.validate():
        artist.name = form.name.data
        artist.city = form.city.data
        artist.state = form.state.data
        artist.phone = form.phone.data
        artist.genres = form.genres.data
        artist.facebook_link = form.facebook_link.data
        artist.image_link = form.image_link.data
        artist.website = form.website_link.data
        artist.seeking_venue = form.seeking_venue.data
        artist.seeking_description = form.seeking_description.data

        db.session.add(artist)
        db.session.commit()
        flash("Artist " + request.form["name"] + " was successfully edited!")
    else:
        db.session.rollback()
        flash(
            "An error occurred. Artist "
            + request.form["name"]
            + " could not be edited."
        )
        db.session.close()
    return redirect(url_for("show_artist", artist_id=artist_id))


#  Shows
#  ----------------------------------------------------------------


@app.route("/shows")
def shows():
    # displays list of shows at /shows
    shows = Show.query.all()
    data = []
    for show in shows:
        info = {
            "venue_id": show.venue_id,
            "venue_name": show.venue.name,
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
        }
        data.append(info)
    return render_template("pages/shows.html", shows=data)


#  Create Show
#  ----------------------------------------------------------------


@app.route("/shows/create")
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template("forms/new_show.html", form=form)


@app.route("/shows/create", methods=["POST"])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    form = ShowForm(request.form)
    if form.validate():
        show = Show(
            artist_id=form.artist_id.data,
            venue_id=form.venue_id.data,
            start_time=form.start_time.data,
        )
        db.session.add(show)
        db.session.commit()
        flash("Show was successfully listed!")
    else:
        db.session.rollback()
        flash("An error occurred. Show could not be listed.")
        db.session.close()
    return render_template("pages/home.html")


@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


if not app.debug:
    file_handler = FileHandler("error.log")
    file_handler.setFormatter(
        Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info("errors")

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == "__main__":
    app.run()

# Or specify port manually:
"""
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
"""
