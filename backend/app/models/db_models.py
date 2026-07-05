from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class DBUser(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="user") # "admin" or "user"

class DBDevice(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    connection_type = Column(String)  # "TCP" or "RTU"
    # TCP fields
    host = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    # RTU fields
    com_port = Column(String, nullable=True)
    baudrate = Column(Integer, nullable=True)
    parity = Column(String, nullable=True)
    bytesize = Column(Integer, nullable=True)
    stopbits = Column(Integer, nullable=True)

    registers = relationship("DBRegister", back_populates="device", cascade="all, delete-orphan")

class DBRegister(Base):
    __tablename__ = "registers"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    name = Column(String)
    address = Column(Integer)
    register_type = Column(String)  # "Coil (FC01)", "Discrete Input (FC02)", "Holding Register (FC03)", "Input Register (FC04)"
    data_type = Column(String)      # "INT16", "UINT16", "INT32", "UINT32", "FLOAT32", "BCD"
    multiplier = Column(Float, default=1.0)
    divisor = Column(Float, default=1.0)
    unit = Column(String, default="")
    limit_min = Column(Float, nullable=True)
    limit_max = Column(Float, nullable=True)

    device = relationship("DBDevice", back_populates="registers")

class DBEmailSettings(Base):
    __tablename__ = "email_settings"
    id = Column(Integer, primary_key=True, default=1)
    smtp_server = Column(String, default="smtp.gmail.com")
    smtp_port = Column(Integer, default=587)
    use_ssl = Column(Boolean, default=False)
    username = Column(String, default="")
    password = Column(String, default="")
    sender_email = Column(String, default="")
    receiver_email = Column(String, default="")
