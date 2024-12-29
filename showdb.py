import psycopg2

# Define your database URL
DATABASE_URL = "postgres://u2e4lm29e9vg22:pe128f7d51bf616d17ce0118375054f0bbc0bed5031eb0a9553f2851ec0e93d64@c5hilnj7pn10vb.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/de5gorvsap72df"

# Establish the connection
connection = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = connection.cursor()

# Query to get all tables in the 'public' schema
cursor.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public';
""")

# Fetch the list of tables
tables = cursor.fetchall()

# Loop through each table and print its data
for table in tables:
    table_name = table[0]
    print(f"\nData in table '{table_name}':")
    
    # Query the data from the table
    cursor.execute(f"SELECT * FROM {table_name};")
    
    # Fetch all rows from the table
    rows = cursor.fetchall()
    
    # Print each row of the table
    for row in rows:
        print(row)

# Close the connection
cursor.close()
connection.close()
