from app import app
from model import db, User, ParkingLot, ParkingSpot, Reservation
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

with app.app_context():
    db.drop_all()
    db.create_all()

    # Create Admin
    admin = User(username='admin', email='admin@example.com', role='admin')
    admin.set_password('admin123')
    db.session.add(admin)

    # Create 5 Users
    users = []
    for i in range(1, 6):
        user = User(
            username=f'user{i}',
            email=f'user{i}@example.com',
            role='user'
        )
        user.set_password('pass123')
        db.session.add(user)
        users.append(user)

    db.session.commit()  # Commit users so they get IDs

    # Create Parking Lots
    lots_data = [
        ("Lot A", "123 Main St", "100001", 10, 20.0),
        ("Lot B", "456 Center Rd", "100002", 10, 25.0),
        ("Lot C", "789 East Ave", "100003", 15, 30.0)
    ]

    lots = []

    for name, address, pincode, max_spots, price in lots_data:
        lot = ParkingLot(
            prime_location_name=name,
            address=address,
            pincode=pincode,
            max_spots=max_spots,
            price=price
        )
        db.session.add(lot)
        lots.append(lot)

    db.session.commit()  # Commit lots to get IDs

    # Create Parking Spots
    all_spots = []
    for lot in lots:
        for i in range(1, lot.max_spots + 1):
            spot = ParkingSpot(
                lot_id=lot.id,
                status='A'  # Initially available
            )
            db.session.add(spot)
            all_spots.append(spot)

    db.session.commit()  # Save all spots

    # Create Past Reservations for 5 users
    used_spots = random.sample(all_spots, 10)  # Pick 10 random spots to have been used

    for i, spot in enumerate(used_spots):
        user = users[i % len(users)]
        in_time = datetime.utcnow() - timedelta(days=random.randint(1, 10), hours=random.randint(1, 6))
        out_time = in_time + timedelta(hours=random.randint(1, 5))
        cost = spot.lot.price

        # Mark some as currently occupied
        if i % 3 == 0:
            out_time = None
            spot.status = 'O'
        else:
            spot.status = 'A'

        res = Reservation(
            spot_id=spot.id,
            user_id=user.id,
            parking_timestamp=in_time,
            leaving_timestamp=out_time,
            cost_per_unit=cost
        )
        db.session.add(res)

    db.session.commit()
    print("Database initialized with admin, users, lots, spots, and sample reservations.")
