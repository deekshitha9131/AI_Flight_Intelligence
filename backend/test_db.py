import asyncpg
import asyncio

async def test_connections():
    print('Testing various connection methods...')

    # Method 1: Try with empty password
    print('\n1. Trying with empty password...')
    try:
        conn = await asyncpg.connect('postgresql://postgres:@localhost:5432/postgres')
        print('   SUCCESS: Connected with empty password!')
        await conn.close()
    except Exception as e:
        print('   FAILED:', str(e)[:100])

    # Method 2: Try with no password specified
    print('\n2. Trying with no password in URL...')
    try:
        conn = await asyncpg.connect('postgresql://postgres@localhost:5432/postgres')
        print('   SUCCESS: Connected with no password!')
        await conn.close()
    except Exception as e:
        print('   FAILED:', str(e)[:100])

    # Method 3: Try as different user
    print('\n3. Trying as different common usernames...')
    for user in ['postgres', 'admin', 'root', '']:
        try:
            if user == '':
                url = f'postgresql://@localhost:5432/postgres'
            else:
                url = f'postgresql://{user}@localhost:5432/postgres'
            conn = await asyncpg.connect(url)
            print(f'   SUCCESS: Connected as user "{user}"!')
            await conn.close()
            return  # Success, we can stop testing
        except Exception as e:
            if user == '':  # Last attempt
                print(f'   FAILED for user "{user}": {str(e)[:100]}')
            else:
                print(f'   FAILED for user "{user}": {str(e)[:50]}...')

    # Method 4: Try to connect and see what authentication methods are supported
    print('\n4. Trying to get more details from connection error...')
    try:
        conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/postgres')
        print('   UNEXPECTED: Connection succeeded!')
        await conn.close()
    except asyncpg.exceptions.InvalidPasswordError as e:
        print('   Got InvalidPasswordError - password is wrong')
    except Exception as e:
        print(f'   Got other error: {type(e).__name__}: {str(e)[:100]}')

    print('\nAll connection attempts completed.')

# Run the async function
asyncio.run(test_connections())