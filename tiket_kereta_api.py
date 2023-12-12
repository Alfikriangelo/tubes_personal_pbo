import pandas as pd
import random
import string
import mysql.connector
from tabulate import tabulate
from sqlalchemy import create_engine

class DatabaseManager:
    def __init__(self, config):
        self.mysql_config = config

    def create_database_tables(self):
        connection = mysql.connector.connect(**self.mysql_config)
        cursor = connection.cursor()

        cursor.execute("SHOW DATABASES LIKE 'kereta_db'")
        database_exists = cursor.fetchone()

        if not database_exists:
            cursor.execute("CREATE DATABASE kereta_db")
            print("Database 'kereta_db' created.")

        cursor.execute("USE kereta_db")

        cursor.execute("SHOW TABLES LIKE 'users'")
        users_table_exists = cursor.fetchone()

        if not users_table_exists:
            cursor.execute("""
                CREATE TABLE users (
                    username VARCHAR(255) PRIMARY KEY,
                    password VARCHAR(255) NOT NULL
                )
            """)
            print("Table 'users' created.")

        cursor.execute("SHOW TABLES LIKE 'tiket'")
        tiket_table_exists = cursor.fetchone()

        if not tiket_table_exists:
            cursor.execute("""
                CREATE TABLE tiket (
                    kode_pemesanan VARCHAR(255) PRIMARY KEY,
                    username VARCHAR(255),
                    nama VARCHAR(255),
                    no_identitas VARCHAR(255),
                    kereta VARCHAR(255),
                    keberangkatan VARCHAR(255),
                    kedatangan VARCHAR(255),
                    harga INT
                )
            """)
            print("Table 'tiket' created.")

        cursor.close()
        connection.close()

    def save_to_txt(self, data_frame, filename):
        data_frame.to_csv(filename, index=False, sep=',')

    def generate_random_code(self, length):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    def save_to_mysql(self, data_frame, table_name):
        connection = mysql.connector.connect(**self.mysql_config)
        try:
            data_frame.to_sql(table_name, con=connection, index=False, if_exists='append')
        finally:
            connection.commit()
            connection.close()

    def read_from_mysql(self, table_name):
        try:
            engine = create_engine(
                f"mysql+mysqlconnector://{self.mysql_config['user']}:{self.mysql_config['password']}@{self.mysql_config['host']}/{self.mysql_config['database']}"
            )
            return pd.read_sql(f'SELECT * FROM {table_name}', con=engine)

        except Exception as e:
            print(f"Error: {e}")

        finally:
            if 'engine' in locals():
                engine.dispose()

class Kereta(DatabaseManager):
    def __init__(self, config):
        super().__init__(config)
        self.__df_users = pd.DataFrame(columns=['username', 'password'])
        self.__logged_in_user = None

    def login(self):
        username = input("Masukkan Username atau ketik 'exit' untuk kembali ke menu: ")

        if username.lower() == 'exit':
            return

        if username not in self._Kereta__df_users['username'].values:
            print("Username tidak ditemukan. Silakan coba lagi.")
            return

        password = input("Masukkan Password: ")

        if self._Kereta__df_users.loc[self._Kereta__df_users['username'] == username, 'password'].values[0] == password:
            print("Login berhasil!")
            self.__logged_in_user = username
            self.menu_user()
        else:
            print("Login gagal. Periksa kembali username dan password.")

    def save_users(self):
        super().save_to_mysql(self.__df_users, 'users')

    def read_data(self):
        self.__df_users = super().read_from_mysql('users')
        self.__df_tiket = super().read_from_mysql('tiket')

    def create_account(self):
        username = input("Masukkan Username baru: ")
        password = input("Masukkan Password baru: ")

        if username in self.__df_users['username'].values:
            print("Username sudah ada. Silakan pilih username lain.")
            return

        try:
            connection = mysql.connector.connect(**self.mysql_config)
            cursor = connection.cursor()

            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            connection.commit()

            self.__df_users.loc[len(self.__df_users)] = [username, password]
            self.save_to_txt(self.__df_users, 'users.txt')

            print("Akun berhasil dibuat!")

            self.read_data()

        except mysql.connector.Error as err:
            print(f"Error: {err}")

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()

class Ticket(Kereta):
    def __init__(self, config):
        super().__init__(config)
        self.__df_tiket = pd.DataFrame(columns=['kode_pemesanan', 'username', 'nama', 'no_identitas', 'kereta', 'keberangkatan', 'kedatangan', 'harga'])

    def calculate_ticket_price(self, departure_station, arrival_station, train_name):
        distance_prices = {
            ('Stasiun Jakarta', 'Stasiun Bandung'): 50000,
            ('Stasiun Jakarta', 'Stasiun Gambir'): 20000,
            ('Stasiun Jakarta', 'Stasiun Brebes'): 80000,
            ('Stasiun Bandung', 'Stasiun Gambir'): 60000,
            ('Stasiun Bandung', 'Stasiun Brebes'): 100000,
            ('Stasiun Bandung', 'Stasiun Jakarta'): 50000,
            ('Stasiun Gambir', 'Stasiun Brebes'): 70000,
            ('Stasiun Gambir', 'Stasiun Jakarta'): 20000,
            ('Stasiun Gambir', 'Stasiun Bandung'): 60000,
            ('Stasiun Brebes', 'Stasiun Jakarta'): 80000,
            ('Stasiun Brebes', 'Stasiun Bandung'): 100000,
            ('Stasiun Brebes', 'Stasiun Gambir'): 70000,
        }

        train_adjustments = {
            'Jaka Tingkir': 10000,
            'Lodaya': 15000,
            'Argo Parahyangan': 20000,
            'Serayu': 22000,
            'Cikuray': 50000,
        }

        key = (departure_station, arrival_station)
        base_price = distance_prices.get(key, 0)

        train_adjustment = train_adjustments.get(train_name, 0)

        return base_price + train_adjustment

    def add_ticket(self):
        if self._Kereta__logged_in_user is None:
            print("Anda harus login terlebih dahulu.")
            return

        available_stations = ['Stasiun Bandung', 'Stasiun Gambir', 'Stasiun Brebes', 'Stasiun Jakarta']
        available_trains = ['Jaka Tingkir', 'Lodaya', 'Argo Parahyangan', 'Serayu', 'Cikuray']

        print("Pilih Stasiun Keberangkatan:")
        for i, station in enumerate(available_stations, start=1):
            print(f"{i}. {station}")

        departure_choice = int(input("Pilih nomor stasiun keberangkatan: "))
        departure_station = available_stations[departure_choice - 1]

        print("Pilih Stasiun Kedatangan:")
        for i, station in enumerate(available_stations, start=1):
            print(f"{i}. {station}")

        arrival_choice = int(input("Pilih nomor stasiun kedatangan: "))
        arrival_station = available_stations[arrival_choice - 1]

        if departure_choice == arrival_choice:
            print("Anda tidak bisa memilih stasiun yang sama")
            return

        print("Pilih Nama Kereta:")
        for i, train in enumerate(available_trains, start=1):
            print(f"{i}. {train}")

        train_choice = int(input("Pilih nomor nama kereta: "))
        train_name = available_trains[train_choice - 1]

        ticket_price = self.calculate_ticket_price(departure_station, arrival_station, train_name)

        num_passengers = int(input("Masukkan Jumlah Penumpang: "))

        total_price = 0

        tiket_list = []

        for _ in range(num_passengers):
            kode_pemesanan = self.generate_random_code(8)
            nama = input("Masukkan Nama Penumpang: ")
            no_identitas = input("Masukkan Nomor Identitas: ")

            tiket_baru = pd.DataFrame({
                'kode_pemesanan': [kode_pemesanan],
                'username': [self._Kereta__logged_in_user],
                'nama': [nama],
                'no_identitas': [no_identitas],
                'kereta': [train_name],
                'keberangkatan': [departure_station],
                'kedatangan': [arrival_station],
                'harga': [int(ticket_price)]
            })

            tiket_list.append(tiket_baru.iloc[0].to_dict())

            total_price += int(ticket_price)

        try:
            connection = mysql.connector.connect(**self.mysql_config)
            cursor = connection.cursor()

            for tiket_baru in tiket_list:
                cursor.execute("""
                    INSERT INTO tiket 
                    (kode_pemesanan, username, nama, no_identitas, kereta, keberangkatan, kedatangan, harga) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, tuple(tiket_baru.values()))

            connection.commit()

            self.__df_tiket = pd.concat([self.__df_tiket, pd.DataFrame(tiket_list)], ignore_index=True)
            self.save_to_txt(self.__df_tiket, 'tiket.txt')
            print(f"Tiket berhasil dibeli! Total Harga: Rp.{total_price}")

            self.read_data()

        except mysql.connector.Error as err:
            print(f"Error: {err}")

        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()

    def view_purchased_tickets(self):
        self.read_data()
        tiket_user = self.__df_tiket[self.__df_tiket['username'] == self._Kereta__logged_in_user]

        if tiket_user.empty:
            print("Anda belum membeli tiket.")
        else:
            print("\nTiket yang dibeli oleh", self._Kereta__logged_in_user)
            print(tabulate(tiket_user, headers='keys', tablefmt='grid'))

    def login(self):
        username = input("Masukkan Username atau ketik 'exit' untuk kembali ke menu: ")

        if username.lower() == 'exit':
            return

        if username not in self._Kereta__df_users['username'].values:
            print("Username tidak ditemukan. Silakan coba lagi.")
            return

        password = input("Masukkan Password: ")

        if self._Kereta__df_users.loc[self._Kereta__df_users['username'] == username, 'password'].values[0] == password:
            print("Login berhasil!")
            self._Kereta__logged_in_user = username
            self.menu_user()
        else:
            print("Login gagal. Periksa kembali username dan password.")

    def menu_user(self):
        while True:
            print("\nMenu:")
            print("1. Beli Tiket")
            print("2. Lihat Tiket yang Dibeli")
            print("3. Logout")

            choice = input("Pilih menu (1/2/3): ")

            if choice == '1':
                self.add_ticket()
            elif choice == '2':
                self.view_purchased_tickets()
            elif choice == '3':
                print("Logout berhasil.")
                break
            else:
                print("Pilihan tidak valid. Silakan pilih lagi.")

ticket_manager = Ticket(config={
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'kereta_db'
})

ticket_manager.read_data()

while True:
    print("\nMenu Utama:")
    print("1. Login")
    print("2. Buat Akun")
    print("3. Keluar")

    choice = input("Pilih menu (1/2/3): ")

    if choice == '1':
        ticket_manager.login()
    elif choice == '2':
        ticket_manager.create_account()
    elif choice == '3':
        print("Keluar dari program.")
        break
    else:
        print("Pilihan tidak valid. Silakan pilih lagi.")
