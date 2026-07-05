from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
  __tablename__ = "users"
  id = Column(Integer, primary_key=True, index=True)
  username = Column(String, unique=True, index=True)
  hashed_password = Column(String)
  role = Column(String, default="user") # "admin" or "user"

class Device(Base):
  __tablename__ = "devices"
  id = Column(Integer, primary_key=True, index=True)
  name = Column(String, unique=True, index=True)
  connection_type = Column(String) # "TCP" or "RTU"
  host = Column(String, nullable=True) # For TCP
  port = Column(Integer, nullable=True) # For TCP
  com_port = Column(String, nullable=True) # For RTU
  baudrate = Column(Integer, nullable=True) # For RTU
  parity = Column(String, nullable=True) # For RTU: "N", "E", "O"
  bytesize = Column(Integer, nullable=True) # For RTU: 5, 6, 7, 8
  stopbits = Column(Integer, nullable=True) # For RTU: 1, 2

  registers = relationship("Register", back_populates="device", cascade="all, delete-orphan")

class Register(Base):
  __tablename__ = "registers"
  id = Column(Integer, primary_key=True, index=True)
  device_id = Column(Integer, ForeignKey("devices.id"))
  name = Column(String)
  address = Column(Integer)
  register_type = Column(String) # e.g. "Holding Register (FC03)"
  data_type = Column(String) # "INT16", "UINT16", "INT32", "UINT32", "FLOAT32", "BCD"
  multiplier = Column(Float, default=1.0)
  divisor = Column(Float, default=1.0)
  unit = Column(String, default="")
  limit_min = Column(Float, nullable=True)
  limit_max = Column(Float, nullable=True)

  device = relationship("Device", back_populates="registers")
  readings = relationship("Reading", back_populates="register", cascade="all, delete-orphan")

class Reading(Base):
  __tablename__ = "readings"
  id = Column(Integer, primary_key=True, index=True)
  register_id = Column(Integer, ForeignKey("registers.id"))
  value = Column(Float)
  timestamp = Column(DateTime, default=datetime.utcnow)

  register = relationship("Register", back_populates="readings")

class SmtpSettings(Base):
  __tablename__ = "smtp_settings"
  id = Column(Integer, primary_key=True, index=True)
  smtp_server = Column(String)
  smtp_port = Column(Integer)
  use_ssl = Column(Boolean, default=True)
  username = Column(String)
  password = Column(String) # Encrypted or plaintext (obfuscated)
  sender_email = Column(String)
  receiver_email = Column(String)
