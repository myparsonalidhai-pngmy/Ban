from flask import Flask, request, send_file
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
API_KEY = "Alone"

def get_player_info(uid, region="IND"):
    """Original info API"""
    url = f"https://grandmixture-id-info.vercel.app/player-info?region={region}&uid={uid}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        return None
    return None

def get_character_info(uid, region="IND"):
    """Character API"""
    url = f"https://anasinfo-rho-orcin.vercel.app/info?uid={uid}&region={region}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        return None
    return None

def get_image(id):
    """Sab images ke liye ek hi function"""
    if not id:
        return None
    url = f"https://iconapi.wasmer.app/{id}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content)).convert("RGBA")
            return img
    except:
        return None
    return None

@app.route('/outfit', methods=['GET'])
def generate():
    uid = request.args.get('uid')
    key = request.args.get('key', 'Alone')
    region = request.args.get('region', 'IND')
    
    if not uid:
        return "Use: /outfit?uid=123456789"
    
    if key != API_KEY:
        return {"error": "Invalid API key"}, 401
    
    # ===== 1. INFO FETCH =====
    player_data = get_player_info(uid, region)
    if not player_data:
        return {"error": "Player not found"}, 404
    
    # ===== 2. CHARACTER INFO FETCH =====
    character_data = get_character_info(uid, region)
    
    character_id = None
    if character_data:
        if 'ProfileInfo' in character_data:
            character_id = character_data['ProfileInfo'].get('CharacterId')
        elif 'CharacterId' in character_data:
            character_id = character_data['CharacterId']
    
    # Player data se info
    info = player_data['AccountInfo']
    profile = player_data['AccountProfileInfo']
    
    name = info.get('AccountName', 'Unknown')
    level = info.get('AccountLevel', 0)
    region_name = info.get('AccountRegion', region)
    likes = info.get('AccountLikes', 0)
    br_rank = info.get('BrMaxRank', 0)
    exp = info.get('AccountEXP', 0)
    season = info.get('AccountSeasonId', 0)
    
    outfit_ids = profile.get('EquippedOutfit', [])[:8]
    weapon_ids = info.get('EquippedWeapon', [])[:2]
    avatar_id = info.get('AccountAvatarId')
    banner_id = info.get('AccountBannerId')
    
    # ===== 3. SAB IMAGES DOWNLOAD =====
    with ThreadPoolExecutor(max_workers=15) as ex:
        banner_future = ex.submit(get_image, banner_id)
        avatar_future = ex.submit(get_image, avatar_id)
        character_future = ex.submit(get_image, character_id) if character_id else None
        outfit_futures = [ex.submit(get_image, oid) for oid in outfit_ids]
        weapon_futures = [ex.submit(get_image, wid) for wid in weapon_ids]
        
        banner_img = banner_future.result()
        avatar_img = avatar_future.result()
        character_img = character_future.result() if character_future else None
        outfit_imgs = [f.result() for f in outfit_futures]
        weapon_imgs = [f.result() for f in weapon_futures]
    
    # ===== 4. CANVAS =====
    W, H = 1600, 1000
    canvas = Image.new('RGB', (W, H), '#0A0A1A')
    draw = ImageDraw.Draw(canvas)
    
    # Background gradient
    for i in range(H):
        ratio = i / H
        draw.line([(0, i), (W, i)], fill=(int(15 + 10*ratio), int(15 + 10*ratio), int(30 + 20*ratio)))
    
    # ===== 5. BANNER - PERFECT CLEAN VERSION (NO EXTRA SIDES) =====
    if banner_img:
        try:
            # Original banner dimensions
            orig_w, orig_h = banner_img.size
            
            # Target banner area (full width, 300px height)
            target_w, target_h = W, 300
            
            # Calculate crop to remove black bars/extra sides
            # We want to use the center portion of the banner
            orig_aspect = orig_w / orig_h
            target_aspect = target_w / target_h
            
            if orig_aspect > target_aspect:
                # Banner is wider than target - crop width
                new_w = int(target_h * orig_aspect)
                new_h = target_h
                banner_resized = banner_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                # Crop center portion
                crop_x = (new_w - target_w) // 2
                banner_clean = banner_resized.crop((crop_x, 0, crop_x + target_w, target_h))
            else:
                # Banner is taller than target - crop height
                new_w = target_w
                new_h = int(target_w / orig_aspect)
                banner_resized = banner_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                # Crop center portion
                crop_y = (new_h - target_h) // 2
                banner_clean = banner_resized.crop((0, crop_y, target_w, crop_y + target_h))
            
            # Paste clean banner
            canvas.paste(banner_clean, (0, 0))
            
            # Add subtle gradient overlay for text readability (optional)
            overlay = Image.new('RGBA', (W, 300), (0, 0, 0, 30))
            canvas.paste(overlay, (0, 0), overlay)
            
        except Exception as e:
            print(f"Banner error: {e}")
            # Fallback gradient banner
            for i in range(300):
                r = int(25 + (i / 300) * 35)
                g = int(10 + (i / 300) * 20)
                b = int(45 + (i / 300) * 55)
                draw.line([(0, i), (W, i)], fill=(r, g, b))
    else:
        # No banner ID - stylish gradient
        for i in range(300):
            r = int(20 + (i / 300) * 40)
            g = int(5 + (i / 300) * 15)
            b = int(60 + (i / 300) * 70)
            draw.line([(0, i), (W, i)], fill=(r, g, b))
        
        try:
            font_banner = ImageFont.truetype("arial.ttf", 32)
            draw.text((W//2 - 150, 130), "✨ PREMIUM BANNER ✨", fill='#FFD700', font=font_banner)
        except:
            draw.text((W//2 - 100, 130), "PREMIUM BANNER", fill='#FFD700')
    
    # Clean gold line - exactly at banner bottom
    draw.line([(0, 300), (W, 300)], fill='#FFD700', width=3)
    
    # Fonts
    try:
        font_title = ImageFont.truetype("arial.ttf", 56)
        font_sub = ImageFont.truetype("arial.ttf", 28)
        font_stat = ImageFont.truetype("arial.ttf", 22)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except:
        font_title = font_sub = font_stat = font_small = ImageFont.load_default()
    
    # ===== 6. AVATAR - square shape =====
    if avatar_img:
        av = avatar_img.resize((130, 130), Image.Resampling.LANCZOS)
        mask = Image.new('L', (130, 130), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (130, 130)], radius=15, fill=255)
        av_out = Image.new('RGBA', (130, 130), (0, 0, 0, 0))
        av_out.paste(av, (0, 0), mask)
        # Gold border
        border = Image.new('RGBA', (138, 138), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border)
        border_draw.rounded_rectangle([(0, 0), (138, 138)], radius=18, outline='#FFD700', width=3)
        border.paste(av_out, (4, 4), av_out)
        canvas.paste(border, (70, 170), border)
    
    # ===== 7. PLAYER INFO =====
    draw.text((230, 180), name, fill='#FFFFFF', font=font_title)
    draw.text((230, 245), f"✦ LEVEL {level} ✦ {region_name} ✦", fill='#FFD700', font=font_sub)
    
    # Stats cards
    stats = [("❤️", str(likes)), ("🏆", str(br_rank)), ("⭐", str(exp)[:6]), ("🎯", str(season))]
    for i, (icon, val) in enumerate(stats):
        x = 230 + (i * 145)
        draw.rectangle([x, 290, x+125, 330], fill='#1A1A2E', outline='#FFD700', width=1)
        draw.text((x+15, 297), icon, fill='#FFD700', font=font_stat)
        draw.text((x+50, 297), val, fill='#FFFFFF', font=font_stat)
    
    # ===== 8. OUTFITS =====
    draw.text((60, 370), "━━━━ EQUIPPED OUTFITS ━━━━", fill='#FFD700', font=font_sub)
    draw.line([(60, 405), (W-60, 405)], fill='#FFD700', width=2)
    
    outfit_pos = [(80, 420), (270, 420), (460, 420), (650, 420), (80, 590), (270, 590), (460, 590), (650, 590)]
    for i, (pos, img) in enumerate(zip(outfit_pos, outfit_imgs)):
        if img:
            o = img.resize((150, 150), Image.Resampling.LANCZOS)
            draw.rectangle([pos[0]-8, pos[1]-8, pos[0]+158, pos[1]+158], fill='#1A1A2E', outline='#FFD700', width=2)
            canvas.paste(o, pos, o)
            draw.text((pos[0]+50, pos[1]+158), f"SLOT {i+1}", fill='#AAAAAA', font=font_small)
    
    # ===== 9. WEAPONS =====
    draw.text((60, 760), "━━━━ WEAPONS ━━━━", fill='#FF4444', font=font_sub)
    draw.line([(60, 795), (W-60, 795)], fill='#FF4444', width=2)
    
    weapon_pos = [(80, 810), (270, 810)]
    for i, (pos, img) in enumerate(zip(weapon_pos, weapon_imgs)):
        if img:
            w = img.resize((150, 150), Image.Resampling.LANCZOS)
            draw.rectangle([pos[0]-8, pos[1]-8, pos[0]+158, pos[1]+158], fill='#1A1A2E', outline='#FF4444', width=2)
            canvas.paste(w, pos, w)
            draw.text((pos[0]+35, pos[1]+158), f"WEAPON {i+1}", fill='#FF8888', font=font_small)
    
    # ===== 10. CHARACTER =====
    if character_img:
        draw.text((W-280, 760), "━━━━ CHARACTER ━━━━", fill='#FF69B4', font=font_sub)
        draw.line([(W-280, 795), (W-60, 795)], fill='#FF69B4', width=2)
        
        c = character_img.resize((140, 140), Image.Resampling.LANCZOS)
        char_x = W-260
        char_y = 810
        draw.rectangle([char_x-8, char_y-8, char_x+148, char_y+148], fill='#1A1A2E', outline='#FF69B4', width=3)
        canvas.paste(c, (char_x, char_y), c)
        draw.text((char_x+25, char_y+152), "CORRECTOR", fill='#FF69B4', font=font_small)
    
    # ===== 11. RIGHT STATS PANEL =====
    draw.rectangle([W-280, 420, W-60, 720], fill='#1A1A2E', outline='#FFD700', width=2)
    draw.text((W-250, 445), "📊 STATISTICS", fill='#FFD700', font=font_sub)
    
    right_stats = [f"UID: {uid}", f"Region: {region_name}", f"Level: {level}", f"Likes: {likes}", 
                   f"BR Rank: {br_rank}", f"EXP: {exp}", f"Season: {season}", 
                   f"Outfits: {len(outfit_ids)}", f"Weapons: {len(weapon_ids)}"]
    if character_id:
        right_stats.append(f"Char ID: {character_id}")
    
    y = 500
    for stat in right_stats:
        draw.text((W-250, y), stat, fill='#CCCCCC', font=font_small)
        y += 35
    
    # ===== 12. FOOTER =====
    draw.text((60, H-40), "⚡ GENERATED BY PREMIUM OUTFIT GENERATOR ⚡", fill='#FFD700', font=font_small)
    
    # Final border
    draw.rectangle([2, 2, W-3, H-3], outline='#FFD700', width=2)
    draw.rectangle([5, 5, W-6, H-6], outline='#FFD700', width=1)
    
    # ===== 13. SEND IMAGE =====
    output = BytesIO()
    canvas.save(output, format='PNG', quality=95)
    output.seek(0)
    return send_file(output, mimetype='image/png')

if __name__ == '__main__':
    print("="*50)
    print("🔥 PERFECT CLEAN BANNER VERSION 🔥")
    print("📍 http://localhost:4000/outfit?uid=YOUR_UID")
    print("✅ Banner: Clean, no extra sides, full width")
    print("✅ Auto-crop removes black bars")
    print("="*50)
    app.run(host='0.0.0.0', port=4000, debug=True)