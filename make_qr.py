import qrcode

# Replace this with your actual Netlify URL once you have it
url = "https://your-church-form.netlify.app"

qr = qrcode.make(url)
qr.save("church_visitor_qr.png")
print("QR code saved! Open church_visitor_qr.png to see it.")