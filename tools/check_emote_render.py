from core.emotes import render_message

message = "audibl7BassGuitar    audibl7Guitar    Kappa    <3    audibl7MusicNotes"
emotes_tag = "53-69/emotesv2_db665b77cefb486183a4938305b6bab6:0-16/emotesv2_87e9f2193ae04e6eb9c59293cda6b40e:21-33/25:38-42/445:47-48"
metadata = {'room-id': '853763018', 'message_id': 'testmsg'}

html, has_img = render_message(message, emotes_tag, metadata)
print('HAS_IMG:', has_img)
print(html)
