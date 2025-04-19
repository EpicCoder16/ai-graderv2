import mysql.connector
from mysql.connector import Error
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database():
    try:
        connection = mysql.connector.connect(
            host="127.0.0.1",
            user="ai_grader_user",
            password="eshwar",
            database="ai_grader",
            auth_plugin='mysql_native_password'
        )
        
        cursor = connection.cursor()
        try:
            # Drop existing tables
            logger.info("Dropping existing tables...")
            cursor.execute("DROP TABLE IF EXISTS comparisons")
            cursor.execute("DROP TABLE IF EXISTS users")
            
            # Create users table
            logger.info("Creating users table...")
            cursor.execute("""
                CREATE TABLE users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create comparisons table
            logger.info("Creating comparisons table...")
            cursor.execute("""
                CREATE TABLE comparisons (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    similarity_score FLOAT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            connection.commit()
            logger.info("Database tables created successfully!")
            
        finally:
            cursor.close()
            connection.close()
            
    except Error as e:
        logger.error(f"Error fixing database: {e}")
        raise

if __name__ == "__main__":
    fix_database() 