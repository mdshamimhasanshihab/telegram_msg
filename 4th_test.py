from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
import io
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Read credentials
file_path = 'credentials.txt'
with open(file_path, 'r') as f:
    lines = f.readlines()
    api_id = lines[0].strip()
    api_hash = lines[1].strip()

# Google API credentials
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = r"C:\Users\Proven\OneDrive\Desktop\Out-source\telegram\Tools\Message(channel_text_info)\telemsg-439207-ec0cc830d6ef.json"
SHEET_ID = '1fbQQVVQsKvRl2FuQVEBIfeSg5QfTq9y0SxyegnkO3ys'
FOLDER_ID = '1xyEGjhIQQd_7AAvbA3J8g9BB1VR7kmJg'  # Folder ID for the target media folder

channel_link = input("Enter the group URL: ")

# Initialize Telegram client
client = TelegramClient('session', api_id, api_hash)

# Function to join the channel
async def join_channel(client, channel_link):
    try:
        await client(JoinChannelRequest(channel_link))
        print(f"Successfully joined the channel: {channel_link}")
    except Exception as e:
        print(f"Failed to join the channel: {e}")

# Function to upload media to Google Drive from memory
async def upload_media_to_drive(message):
    if message.media:
        # Use BytesIO to hold the media in memory
        media_stream = io.BytesIO()
        
        # Download the media to the BytesIO stream
        await client.download_media(message, media_stream)
        media_stream.seek(0)  # Reset the stream position to the beginning
        
        service = build('drive', 'v3', credentials=google.auth.load_credentials_from_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)[0])
        
        media = MediaIoBaseUpload(media_stream, mimetype='application/octet-stream')
        
        file_metadata = {
            'name': f"{message.id}.jpg",  # Change extension based on the media type
            'parents': [FOLDER_ID]
        }

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        print(f"File uploaded to Drive with ID: {file.get('id')}")
        return f"https://drive.google.com/uc?id={file.get('id')}"  # Return the link to the uploaded file

    return None  # In case there's no media

# Function to convert UTC time to local time zone and return only time
def convert_to_local_time(utc_datetime):
    local_time = utc_datetime.astimezone().strftime("%I:%M %p")  # Example: 01:14 PM
    return local_time

# Function to save messages to Google Sheets
async def save_to_google_sheets(messages_data):
    service = build('sheets', 'v4', credentials=google.auth.load_credentials_from_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)[0])
    sheet = service.spreadsheets()

    # Prepare data for Google Sheets
    values = [[msg["message"], str(msg["date"]), msg["time"], msg["channel"], msg["media_link"]] for msg in messages_data]

    # Append data to the Google Sheet
    body = {
        'values': values
    }
    
    result = sheet.values().append(
        spreadsheetId=SHEET_ID,
        range="Sheet1!A:E",  # Adjust range as needed
        valueInputOption="RAW",
        body=body
    ).execute()
    
    print(f"{result.get('updates').get('updatedCells')} cells appended.")

# Event handler for new messages
@client.on(events.NewMessage(chats=channel_link))
async def new_message_listener(event):
    message_info = {
        "message": event.message.text if event.message.text else "Media message",
        "date": event.message.date.date(),  # Keep the date separate
        "time": convert_to_local_time(event.message.date),  # Only time in HH:MM AM/PM
        "channel": channel_link.split('/')[-1],  # Use channel name or ID
        "media_link": None   # Placeholder for media link
    }

    # Check if there is media in the message
    if event.message.media:
        media_link = await upload_media_to_drive(event.message)
        message_info["media_link"] = media_link

    # Save message to Google Sheets
    await save_to_google_sheets([message_info])

# Main function to join the channel and listen for new messages
async def main():
    await join_channel(client, channel_link)
    print("Listening for new messages...")

# Run the client and start the loop
with client:
    client.loop.run_until_complete(main())
    client.run_until_disconnected()  # Keep the script running to listen for new messages
client.disconnect()