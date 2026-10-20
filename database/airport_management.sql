USE airport_management;
CREATE TABLE users(
user_id INT AUTO_INCREMENT PRIMARY KEY,
name VARCHAR(100) NOT NULL,
email VARCHAR(70) NOT NULL UNIQUE,
password VARCHAR(100) NOT NULL,
role VARCHAR(150) NOT NULL);
CREATE TABLE passengers (
    passenger_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    phone VARCHAR(15) NOT NULL,
    gender VARCHAR(20),
    date_of_birth DATE,
    passport_no VARCHAR(20) UNIQUE,

    CONSTRAINT fk_passenger_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
CREATE TABLE airlines (
    airline_id INT AUTO_INCREMENT PRIMARY KEY,
    airline_name VARCHAR(100) NOT NULL,
    airline_code VARCHAR(10) NOT NULL UNIQUE,
    country VARCHAR(50) NOT NULL
);
CREATE TABLE gates (
    gate_id INT AUTO_INCREMENT PRIMARY KEY,
    gate_number VARCHAR(10) NOT NULL UNIQUE,
    terminal VARCHAR(20) NOT NULL,
    status VARCHAR(30) NOT NULL
);
CREATE TABLE flights (
    flight_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_number VARCHAR(20) NOT NULL UNIQUE,
    airline_id INT NOT NULL,
    source VARCHAR(100) NOT NULL,
    destination VARCHAR(100) NOT NULL,
    departure_time DATETIME NOT NULL,
    arrival_time DATETIME NOT NULL,
    gate_id INT,
    status VARCHAR(30) NOT NULL,
    total_seats INT NOT NULL,
    available_seats INT NOT NULL,

    CONSTRAINT fk_flight_airline
        FOREIGN KEY (airline_id)
        REFERENCES airlines(airline_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_flight_gate
        FOREIGN KEY (gate_id)
        REFERENCES gates(gate_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);
CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    passenger_id INT NOT NULL,
    flight_id INT NOT NULL,
    booking_date DATETIME NOT NULL,
    seat_number VARCHAR(10) NOT NULL,
    class VARCHAR(20) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    booking_status VARCHAR(30) NOT NULL,

    CONSTRAINT fk_booking_passenger
        FOREIGN KEY (passenger_id)
        REFERENCES passengers(passenger_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_booking_flight
        FOREIGN KEY (flight_id)
        REFERENCES flights(flight_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);
CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_date DATETIME NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    payment_status VARCHAR(30) NOT NULL,

    CONSTRAINT fk_payment_booking
        FOREIGN KEY (booking_id)
        REFERENCES bookings(booking_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
CREATE TABLE employees (
    employee_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    position VARCHAR(100) NOT NULL,
    salary DECIMAL(10,2) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE
);