import psycopg2
import os

# Establishing the connection
#DATABASE_URL = os.environ['DATABASE_URL']
DATABASE_URL = 'postgres://u2e4lm29e9vg22:pe128f7d51bf616d17ce0118375054f0bbc0bed5031eb0a9553f2851ec0e93d64@c5hilnj7pn10vb.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/de5gorvsap72df'
CONNECTION = psycopg2.connect(DATABASE_URL, sslmode='require')
CURSOR = CONNECTION.cursor()

def getAllIDs():
    CURSOR.execute("""
        SELECT
            id 
        FROM
            results              
    ;""")
    all = CURSOR.fetchall()
    return all

def getID():
    CURSOR.execute("""
        SELECT
            id
        FROM
            results
        WHERE
            rate IS NULL AND convo IS NULL AND total IS NULL AND match_status IS NULL
        LIMIT 1;
    """)
    id = CURSOR.fetchone()
    CONNECTION.commit()
    return id[0] if id else None

def getUnmatchedIDs():
    CURSOR.execute("""
        SELECT
            id
        FROM
            results
        WHERE
            match_status IS NULL;
    """)
    ids = CURSOR.fetchall()
    CONNECTION.commit()
    return ids

def insertPulses(id, time, heartrate1, heartrate2):
    query = """
        INSERT INTO 
            heartrate (
                id,
                time,
                heartrate1,
                heartrate2
            )
        VALUES (%s, %s, %s, %s);
    """
    CURSOR.execute(query, (id, time, heartrate1, heartrate2))
    CONNECTION.commit()

def addUserPair(user1, user2): 
    """
    Adds a pair to the pairs table. Ensures both users exist in the users table first.
    """
    # Ensure user1 exists in the users table
    CURSOR.execute("""
        INSERT INTO users (username, password, first_name, last_name)
        VALUES (%s, 'default_password', 'default_first', 'default_last')
        ON CONFLICT (username) DO NOTHING;
    """, (user1,))
    
    # Ensure user2 exists in the users table
    CURSOR.execute("""
        INSERT INTO users (username, password, first_name, last_name)
        VALUES (%s, 'default_password', 'default_first', 'default_last')
        ON CONFLICT (username) DO NOTHING;
    """, (user2,))
    
    CONNECTION.commit()
    
    # Add a new entry to the results table
    CURSOR.execute("""
        INSERT INTO
            results (
                rate,
                convo,
                total,
                match_status
            )
        VALUES (
            NULL, NULL, NULL, NULL
        );
    """)
    CONNECTION.commit()
    
    # Get the ID of the newly created result
    id = getID()

    # Add the pair to the pairs table
    query = """
        INSERT INTO
            pairs (
                pairid,
                id1,
                id2
            )
        VALUES 
            (%s, %s, %s)
        ;
    """
    CURSOR.execute(query, (id, user1, user2))
    CONNECTION.commit()


def addUser(username, password, first_name, last_name):
    CURSOR.execute("""
        INSERT INTO
            users (
                username,
                password,
                first_name,
                last_name
            )
        VALUES 
            (%s, %s, %s, %s)
        ;
    """)
    CONNECTION.commit()


def getScores(id):
    CURSOR.execute("""
        SELECT
            rate,
            convo,
            total
        FROM
            results
        WHERE
            id = %s;
    """, (id,))
    scores = CURSOR.fetchall()
    return scores

def getPulse(id):
    CURSOR.execute("""
        SELECT
            heartrate1,
            heartrate2
        FROM
            heartrate
        WHERE
            id = %s;
    """, (id,))
    pulses = CURSOR.fetchall()
    return pulses

def getResults(id):
    CURSOR.execute("""
        SELECT
            *
        FROM
            results
        WHERE id = %s;
    ;""", (id,))
    results = CURSOR.fetchall()
    return results

def updateMatch(match_status, id): 
    CURSOR.execute("""
        UPDATE
            results
        SET
            match_status = %s
        WHERE
            id = %s;
    """, (match_status, id))
    print("updated")
    CONNECTION.commit()

def updateScores(aff, vuln, kind, other, neg, expl, rate, convo, total, id):
    CURSOR.execute("""
        UPDATE
            results
        SET
            affection = %s,
            vulnerability = %s,
            kindness = %s,
            other = %s,
            negative = %s,
            explanation = %s,
            rate = %s,
            convo = %s,
            total = %s
        WHERE
            id = %s;
    """, (aff, vuln, kind, other, neg, expl, rate, convo, total, id))
    print("updated")
    CONNECTION.commit()

def updateImprovement(id, notes):
    CURSOR.execute("""
        UPDATE 
            users
        SET 
            improvement = %s
        WHERE 
            users = %s
    ;""", (notes, id))
    CURSOR.commit()

### Processing

def setup():
    # Create tables
    CURSOR.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id SERIAL PRIMARY KEY,
            affection INTEGER,
            vulnerability INTEGER,
            kindness INTEGER,
            other INTEGER,
            negative INTEGER,
            explanation TEXT,
            rate INTEGER,
            convo INTEGER,
            total INTEGER,
            match_status INTEGER
        );
    """)

    CURSOR.execute("""
        CREATE TABLE IF NOT EXISTS heartrate (
            id INTEGER REFERENCES results(id),
            time BIGINT,
            heartrate1 INTEGER,
            heartrate2 INTEGER
        );
    """)

    CURSOR.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            first_name TEXT,
            last_name TEXT,
            improvement TEXT
        );
    """)

    CURSOR.execute("""
        CREATE TABLE IF NOT EXISTS pairs (
            pairid SERIAL PRIMARY KEY,
            id1 TEXT REFERENCES users(username),
            id2 TEXT REFERENCES users(username)
        );
    """)

    CONNECTION.commit()

def deletePair(id):
    """
    Deletes a contact from the contact database.
    :param id: int -> primary key
    :return: None
    """
    CURSOR.execute("""
        DELETE FROM
            results
        WHERE
            id = %s;
    """, (id,))
    CURSOR.execute("""
        DELETE FROM
            heartrate
        WHERE
            id = %s;
    """, (id,))
    CONNECTION.commit()

def delete_all_tables():
    """
    Deletes all tables in the public schema using the globally defined CURSOR and CONNECTION.
    """
    try:
        # Fetch all table names in the public schema
        CURSOR.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public';
        """)
        tables = CURSOR.fetchall()
        
        # Drop each table dynamically
        for table in tables:
            CURSOR.execute(f"DROP TABLE IF EXISTS {table[0]} CASCADE;")
            print(f"Deleted table: {table[0]}")
        
        CONNECTION.commit()
        print("All tables deleted successfully.")
    except psycopg2.Error as e:
        print(f"Error deleting tables: {e}")


if __name__ == "__main__":
    #delete_all_tables()
    #setup()

    print(getResults(1))
    print(getResults(2))
    print(getResults(3))
    
    """
    setup()
    addUserPair("alicia", "a")
    id = getID()
    #print(id)
    #insertPulses(id, 10, 60, 60)
    #insertPulses(id, 20, 60, 60)
    updateScores(1, 1, 1, 1, 9, " ", 8, 4, 6, id)
    #updateMatch(70, id)
    #print(getPulse(id))
    print(getScores(id))


    print(getUnmatchedIDs)
    addUserPair("cat", "dog")
    id = getID()
    #print(id)
    #insertPulses(id, 0, 0, 0)
    #insertPulses(id, 20, 60, 60)
    updateScores(10, 5, 6, 6, 9, " ", 8, 4, 5, id)
    #updateMatch(1, id)
    #print(getPulse(id))
    print(getScores(id))
    print(getUnmatchedIDs)
    print(getAllIDs)

    addUserPair("Alicia", "Shivani")
    id = getID()
    updateScores(10, 5, 6, 6, 9, " ", 8, 4, 5, id)
    

    ## delete heartrate table"""
