from flask import Flask, render_template, request, redirect, url_for, session, flash
from model import db, User, ParkingLot, ParkingSpot, Reservation
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.before_request
def create_tables_once():
    if not hasattr(app, 'db_initialized'):
        db.create_all()
        app.db_initialized = True

# Home
@app.route('/')
def home():
    return redirect('/login')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            return redirect('/admin/dashboard' if user.is_admin else '/user/dashboard')
        else:
            flash('Invalid credentials.')
    return render_template('login.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already exists.')
        else:
            user = User(name=name, email=email, password=password, is_admin=False)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful. Please login.')
            return redirect('/login')
    return render_template('register.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# Admin Dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect('/login')
    lots = ParkingLot.query.all()
    return render_template('admin_dashboard.html', lots=lots)

# Add Lot
@app.route('/admin/add_lot', methods=['GET', 'POST'])
def add_lot():
    if not session.get('is_admin'):
        return redirect('/login')
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pincode = request.form['pincode']
        price = float(request.form['price'])
        max_spots = int(request.form['max_spots'])
        lot = ParkingLot(name=name, address=address, pincode=pincode, price=price, max_spots=max_spots)
        db.session.add(lot)
        db.session.commit()
        for i in range(1, max_spots + 1):
            spot = ParkingSpot(lot_id=lot.id, number=i, status='A')
            db.session.add(spot)
        db.session.commit()
        return redirect('/admin/dashboard')
    return render_template('admin_add_lot.html')

# View Users
@app.route('/admin/users')
def admin_users():
    if not session.get('is_admin'):
        return redirect('/login')
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin_view_users.html', users=users)

# View Spots in Lot
@app.route('/admin/view_spots/<int:lot_id>')
def admin_view_spots(lot_id):
    if not session.get('is_admin'):
        return redirect('/login')
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()
    return render_template('admin_view_spots.html', lot=lot, spots=spots)

# User Dashboard
@app.route('/user/dashboard')
def user_dashboard():
    if session.get('is_admin') or not session.get('user_id'):
        return redirect('/login')
    lots = ParkingLot.query.all()
    return render_template('user_dashboard.html', lots=lots)

# Book Spot
@app.route('/user/book/<int:lot_id>')
def book_spot(lot_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')
    spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
    if spot:
        spot.status = 'O'
        reservation = Reservation(user_id=user_id, spot_id=spot.id, parking_timestamp=datetime.now())
        db.session.add(reservation)
        db.session.commit()
        flash(f"Spot {spot.number} booked.")
    else:
        flash("No available spots.")
    return redirect('/user/dashboard')

# Release Spot
@app.route('/user/release/<int:reservation_id>')
def release_spot(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.leaving_timestamp:
        flash("Already released.")
    else:
        reservation.leaving_timestamp = datetime.now()
        duration = (reservation.leaving_timestamp - reservation.parking_timestamp).seconds / 3600
        lot = reservation.spot.lot
        reservation.cost = round(duration * lot.price, 2)
        reservation.spot.status = 'A'
        db.session.commit()
        flash(f"Released. Cost: ₹{reservation.cost}")
    return redirect('/user/summary')

# User Summary
@app.route('/user/summary')
def user_summary():
    user_id = session.get('user_id')
    reservations = Reservation.query.filter_by(user_id=user_id).all()
    return render_template('user_parking_summary.html', reservations=reservations)

# 404
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
