from flask import Flask, render_template, redirect, request, session, url_for, g
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secretkey'
DATABASE = 'parking.db'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Create tables
        cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'user'))
        );

        CREATE TABLE IF NOT EXISTS parking_lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            pincode TEXT NOT NULL,
            price REAL NOT NULL,
            max_spots INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS parking_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER,
            status TEXT CHECK(status IN ('Available', 'Occupied')) DEFAULT 'Available',
            FOREIGN KEY (lot_id) REFERENCES parking_lots(id)
        );

        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            spot_id INTEGER,
            in_time TEXT,
            out_time TEXT,
            cost REAL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (spot_id) REFERENCES parking_spots(id)
        );
        ''')

        # Add default admin if not exists
        cursor.execute("SELECT * FROM users WHERE role = 'admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                           ('admin', 'admin123', 'admin'))

        db.commit()


@app.route('/')
def home():
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            if user[3] == 'admin':
                return redirect('/admin/dashboard')
            else:
                return redirect('/user/dashboard')
        else:
            error = 'Invalid credentials.'
    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                       (username, password, 'user'))
            db.commit()
            return redirect('/login')
        except sqlite3.IntegrityError:
            error = 'Username already exists.'
    return render_template('register.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for('login'))

    lots = ParkingLot.query.all()
    total_lots = len(lots)
    total_spots = ParkingSpot.query.count()
    occupied_spots = ParkingSpot.query.filter_by(status='O').count()

    return render_template('admin_dashboard.html', lots=lots, total_lots=total_lots,
                           total_spots=total_spots, occupied_spots=occupied_spots)


@app.route('/admin/add_lot', methods=['GET', 'POST'])
def add_lot():
    if session.get("role") != "admin":
        return redirect(url_for('login'))

    error = None
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pincode = request.form['pincode']
        price = request.form['price']
        max_spots = int(request.form['max_spots'])

        if not name or not address or not pincode or not price:
            error = "All fields are required"
        else:
            lot = ParkingLot(name=name, address=address, pincode=pincode,
                             price=price, max_spots=max_spots)
            db.session.add(lot)
            db.session.commit()
            for _ in range(max_spots):
                spot = ParkingSpot(lot_id=lot.id, status='A')
                db.session.add(spot)
            db.session.commit()
            return redirect(url_for('admin_dashboard'))

    return render_template('admin_add_lot.html', error=error)


@app.route('/admin/edit_lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_lot(lot_id):
    if session.get("role") != "admin":
        return redirect(url_for('login'))

    lot = ParkingLot.query.get_or_404(lot_id)
    error = None

    if request.method == 'POST':
        lot.name = request.form['name']
        lot.address = request.form['address']
        lot.pincode = request.form['pincode']
        lot.price = request.form['price']
        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_edit_lot.html', lot=lot, error=error)


@app.route('/admin/delete_lot/<int:lot_id>')
def delete_lot(lot_id):
    if session.get("role") != "admin":
        return redirect(url_for('login'))

    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()

    if any(spot.status == 'O' for spot in spots):
        return "Cannot delete: Some spots are still occupied"

    for spot in spots:
        db.session.delete(spot)
    db.session.delete(lot)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/view_spots/<int:lot_id>')
def view_spots(lot_id):
    if session.get("role") != "admin":
        return redirect(url_for('login'))

    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
    return render_template('admin_view_spots.html', lot=lot, spots=spots)


@app.route('/admin/delete_spot/<int:spot_id>')
def delete_spot(spot_id):
    if session.get("role") != "admin":
        return redirect(url_for('login'))

    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.status == 'O':
        return "Cannot delete: Spot is currently occupied."

    lot_id = spot.lot_id
    db.session.delete(spot)
    db.session.commit()
    return redirect(url_for('view_spots', lot_id=lot_id))


@app.route('/admin/users')
def view_users():
    if session.get("role") != "admin":
        return redirect(url_for('login'))

    users = User.query.filter_by(role='user').all()
    return render_template('admin_view_users.html', users=users)

@app.route('/user/dashboard')
def user_dashboard():
    if session.get("role") != "user":
        return redirect(url_for('login'))
    user = User.query.get(session["user_id"])
    lots = ParkingLot.query.all()
    active = Reservation.query.filter_by(user_id=user.id, out_time=None).first()
    return render_template('user_dashboard.html', user=user, lots=lots, active_reservation=active)


@app.route('/user/book', methods=["POST"])
def book_spot():
    if session.get("role") != "user":
        return redirect(url_for('login'))

    lot_id = request.form["lot_id"]
    spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
    if not spot:
        return "No available spots."

    spot.status = 'O'
    reservation = Reservation(user_id=session["user_id"], spot_id=spot.id, in_time=datetime.now())
    db.session.add(reservation)
    db.session.commit()
    return redirect(url_for('user_dashboard'))


@app.route('/user/release/<int:spot_id>')
def release_spot(spot_id):
    if session.get("role") != "user":
        return redirect(url_for('login'))

    spot = ParkingSpot.query.get_or_404(spot_id)
    reservation = Reservation.query.filter_by(spot_id=spot.id, user_id=session["user_id"], out_time=None).first()

    if not reservation:
        return "Reservation not found."

    reservation.out_time = datetime.now()
    duration = (reservation.out_time - reservation.in_time).total_seconds() / 3600
    reservation.cost = round(duration * spot.lot.price, 2)

    spot.status = 'A'
    db.session.commit()
    return redirect(url_for('user_dashboard'))


@app.route('/user/summary')
def user_summary():
    if session.get("role") != "user":
        return redirect(url_for('login'))

    user_id = session["user_id"]
    reservations = Reservation.query.filter_by(user_id=user_id).order_by(Reservation.in_time.desc()).all()

    data = {
        "labels": [r.lot.name for r in reservations],
        "datasets": [{
            "label": "Costs (₹)",
            "data": [r.cost or 0 for r in reservations],
            "backgroundColor": "rgba(255, 99, 132, 0.5)"
        }]
    }
    return render_template("user_parking_summary.html", reservations=reservations, chart_data=json.dumps(data))



if __name__ == '__main__':
    init_db()
    app.run(debug=True)
