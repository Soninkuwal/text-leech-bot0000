import asyncio
import os
import re
import subprocess
import sys
import time
from typing import Any

import aiohttp
import requests
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, exceptions
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from pyrogram.types.messages_and_media import Message
from utils.vars import API_HASH, API_ID, BOT_TOKEN, WEBHOOK, PORT
from utils.helper import (
    getstatusoutput,
    is_youtube_link,
    remove_chars,
    remove_duplicate_line,
    replace_space,
    is_valid_link,
)

from aiohttp import web


Ashu = Client("Ashu", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

START_TEXT = """
**Hi, I am an advanced bot that can download various media such as videos, audios, pdf, etc. and much more.
Click on the commands to know more about my working.**
\n\n
`Commands`
/dl - To Download Any Media using Direct link (Youtube, etc.)
/batch - To Download From Youtube Playlist or Google Drive folders, etc.
/extract - To Extract audio from any video you send.
/web - To Access and Navigate Website without going on it.

\n\n
**Developer »** [Ashutosh](https://github.com/AshutoshGoswami24) 
**Support »** [AshuSupport](https://t.me/AshuSupport)
"""


@Ashu.on_message(filters.command(["start", "help"]))
async def start(client, message):
    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Developer", url="https://github.com/AshutoshGoswami24"
                ),
                InlineKeyboardButton(text="Support", url="https://t.me/AshuSupport"),
            ]
        ]
    )
    await message.reply_text(START_TEXT, reply_markup=reply_markup)


@Ashu.on_message(filters.command("stop"))
async def stop(client, message):
    await message.reply_text("Bot Stopped...")
    os._exit(0)


@Ashu.on_message(filters.command("restart"))
async def restart_handler(client, message):
    await message.reply_text("Restarting...")
    os.execl(sys.executable, sys.executable, *sys.argv)


@Ashu.on_message(filters.command("upload"))
async def upload(client, message):
    try:
        if len(message.command) != 2:
            await message.reply_text("Please enter file path along with the command...")
            return

        path = message.command[1]
        if not os.path.exists(path):
            await message.reply_text(
                "File not found. Please ensure that the file path is correct..."
            )
            return

        file = path.split("/")[-1]
        await client.send_document(message.chat.id, path, caption=file)

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")


@Ashu.on_message(filters.command("dl"))
async def download_video(client, message):
    if len(message.command) != 2:
        await message.reply_text("Please give the link to download...")
        return

    link = message.command[1]
    if not is_valid_link(link):
        await message.reply_text(
            "Please check the link. It should be a valid one"
        )
        return
    prog = await message.reply_text("Downloading...")
    file_name = await get_file_name_from_link(link)
    if file_name is None:
        file_name = "downloaded.mkv"
    if not os.path.exists("./downloads"):
      os.makedirs("./downloads")
    if is_youtube_link(link):
        download_cmd = f'yt-dlp -o "./downloads/{file_name}" -f "bestvideo[height<=1080]+bestaudio" --hls-prefer-ffmpeg --no-keep-video --remux-video mkv --no-warning "{link}"'

        status, output = getstatusoutput(download_cmd)
        if status != 0:
            download_cmd = f'yt-dlp -i -f "bestvideo[height<=1080]+bestaudio" --no-keep-video --remux-video mkv --no-warning "{link}" -o "./downloads/{file_name}"'
            status, output = getstatusoutput(download_cmd)
            if status != 0:
                await prog.edit_text(f"Error: {output}")
                return
    else:
        download_cmd = f'yt-dlp -f "bestvideo+bestaudio" --no-keep-video --remux-video mkv "{link}" -o "./downloads/{file_name}"'
        status, output = getstatusoutput(download_cmd)
        if status != 0:
            await prog.edit_text(f"Error: {output}")
            return
    
    downloaded_file_path = f"./downloads/{file_name}"

    if os.path.exists(downloaded_file_path):
        await prog.edit_text("Uploading...")
        try:
            await client.send_document(message.chat.id, downloaded_file_path, caption=file_name)
        except FloodWait as e:
            await prog.edit_text(f"FloodWait: {str(e)}")
            await asyncio.sleep(e.x)
            await client.send_document(message.chat.id, downloaded_file_path, caption=file_name)

        except Exception as e:
            await prog.edit_text(f"Error: {str(e)}")
    else:
        await prog.edit_text("No file downloaded")

    try:
        os.remove(downloaded_file_path)
    except Exception as e:
        print(str(e))
    try:
        os.remove("thumb.jpg")
    except Exception as e:
        print(str(e))


@Ashu.on_message(filters.command("batch"))
async def batch_download(client, message):
    if len(message.command) != 2:
        await message.reply_text(
            "Please provide the text file with links."
        )
        return

    input0 = message.command[1]

    if not os.path.exists(input0):
        await message.reply_text("File not found...")
        return
    
    res = await message.reply_text("Downloading...")
    with open(input0, "r") as f:
        raw_text = f.read().splitlines()

    links = []
    for link in raw_text:
        if is_valid_link(link):
            links.append(link)
    if len(links) == 0:
         await res.edit_text("No valid links found in file")
         return
    
    if not os.path.exists("./downloads"):
         os.makedirs("./downloads")
    
    count = 1
    for link in links:
            try:
                    prog = await message.reply_text(f"Downloading {count}/{len(links)}")
                    file_name = await get_file_name_from_link(link)
                    if file_name is None:
                         file_name = f"download_{count}.mkv"
                    else:
                        file_name = f"download_{count}_{file_name}"
                    
                    if is_youtube_link(link):
                        download_cmd = f'yt-dlp -o "./downloads/{file_name}" -f "bestvideo[height<=1080]+bestaudio" --hls-prefer-ffmpeg --no-keep-video --remux-video mkv --no-warning "{link}"'
                        status, output = getstatusoutput(download_cmd)
                        if status != 0:
                            download_cmd = f'yt-dlp -i -f "bestvideo[height<=1080]+bestaudio" --no-keep-video --remux-video mkv --no-warning "{link}" -o "./downloads/{file_name}"'
                            status, output = getstatusoutput(download_cmd)
                            if status != 0:
                                    await prog.edit_text(f"Error: {output}")
                                    continue
                    else:
                            download_cmd = f'yt-dlp -f "bestvideo+bestaudio" --no-keep-video --remux-video mkv "{link}" -o "./downloads/{file_name}"'
                            status, output = getstatusoutput(download_cmd)
                            if status != 0:
                                await prog.edit_text(f"Error: {output}")
                                continue
                    
                    downloaded_file_path = f"./downloads/{file_name}"

                    if os.path.exists(downloaded_file_path):
                        await prog.edit_text("Uploading...")
                        try:
                                await client.send_document(message.chat.id, downloaded_file_path, caption=f"Batch {file_name}")
                        except FloodWait as e:
                                await prog.edit_text(f"FloodWait: {str(e)}")
                                await asyncio.sleep(e.x)
                                await client.send_document(message.chat.id, downloaded_file_path, caption=f"Batch {file_name}")

                        except Exception as e:
                                await prog.edit_text(f"Error: {str(e)}")
                    else:
                        await prog.edit_text("No file downloaded")

                    try:
                        os.remove(downloaded_file_path)
                    except Exception as e:
                         print(str(e))
                    try:
                         os.remove("thumb.jpg")
                    except Exception as e:
                            print(str(e))
                    count += 1
            except Exception as e:
                await res.edit_text(f"Error : {str(e)}")
                continue
    await res.edit_text("Completed")



@Ashu.on_message(filters.command("web"))
async def web_navigate(client, message):
    if len(message.command) != 2:
        await message.reply_text("Please give the website link")
        return

    link = message.command[1]

    if not is_valid_link(link):
        await message.reply_text("Please give valid URL")
        return

    try:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Referer": "http://www.visionias.in/",
            "Sec-Fetch-Dest": "iframe",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36",
            "sec-ch-ua": '"Chromium";v="107", "Not=A?Brand";v="24"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
        }
        resp = requests.get(link, headers=headers)
        resp.raise_for_status()
        await message.reply_text(resp.text)
    except requests.exceptions.RequestException as e:
        await message.reply_text(f"Error:{str(e)}")


@Ashu.on_message(filters.command("extract"))
async def extract_audio(client, message):
    if message.reply_to_message is None:
        await message.reply_text("Please reply to the video you want to extract...")
        return

    if message.reply_to_message.video is None:
        await message.reply_text("Please reply to the video you want to extract...")
        return

    prog = await message.reply_text("Downloading...")
    file = await client.download_media(message.reply_to_message)
    file_name = file.split("/")[-1]
    file_name = file_name.split(".")[0]
    cmd = f'ffmpeg -i "{file}" -vn -acodec libmp3lame "{file_name}.mp3"'
    status, output = getstatusoutput(cmd)
    if status != 0:
        await prog.edit_text(f"Error: {output}")
        return
    await prog.edit_text("Uploading Audio...")
    try:
        await client.send_document(
            message.chat.id, f"{file_name}.mp3", caption="Audio"
        )
    except Exception as e:
        await prog.edit_text(f"Error: {str(e)}")
    try:
        os.remove(file)
        os.remove(f"{file_name}.mp3")
    except Exception as e:
        print(str(e))


@Ashu.on_message(filters.text)
async def highlighter(client, message):
    text = message.text
    input1 = re.search(r"(https://.*playlist.m3u8.*?)\"", text)
    if input1:
        await message.reply_text(input1.group(1))

    input2 = re.search(
        r"https://api.classplusapp.com/cams/uploader/video/jw-signed-url\?url=(.*?)x-access-token",
        text,
    )
    if input2:
        res = input2.group(1)
        output = f"https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={res}&x-access-token={input2.group(0).split('x-access-token')[1]}"
        await message.reply_text(output)

    input3 = re.search(r"(https://.*?utkarshapp.com.*?)\"", text)
    if input3:
        res = input3.group(1)
        output = res.replace("/utkarshapp.com", "/master.mpd")
        await message.reply_text(output)

    input4 = re.search(r"(https://.*?cloudfront.net.*?)\"", text)
    if input4:
        res = input4.group(1)
        output = res.replace("/master.mpd", "/master.m3u8")
        await message.reply_text(output)

    input6 = re.search(r"(https://.*youtube.*?)\"", text)
    if input6:
        await message.reply_text(input6.group(1))


async def get_file_name_from_link(link):
    try:
        cmd = f'yt-dlp --get-filename "{link}"'
        status, output = getstatusoutput(cmd)
        if status != 0:
            return None
        file_name = output.strip()
        file_name = replace_space(file_name)
        return file_name
    except Exception as e:
        print(str(e))
        return None


async def root_route_handler(request):
    return web.Response(text="This is a webhook route")

async def setup(app: web.Application):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()


async def main():
    app = web.Application()
    app.add_routes([web.get("/", root_route_handler)])

    asyncio.create_task(setup(app))
    print("Web server started on port", PORT)
    await Ashu.start()
    print("Bot Started...")
    await asyncio.gather(
        Ashu.run_forever(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot Stopped...")