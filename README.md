# Anki-autoLapseNewInterval
An Anki2 addon by [eshapard](https://github.com/eshapard) which I made work with Anki21. The addon automatically adjusts the new interval to target an 85% review success rate. A more in-depth description can be found on [eshapard's code blog.](https://eshapard.github.io/anki/anki-auto-adjust-new-interval-after-a-lapse.html)
# Changes
While eshapard's code blog mentions that the addon might work with Anki21 if you comment out a particular line, I discovered that lapses are rarely registered as such, and so the addon only adjusted the new interval on the first time you run it, and *never again*, because even if I lapsed 50 cards, they would not be detected on Anki21.
  
I don't know if this is due to the Anki21 migration, an original bug in the Anki2 addon, or the author's intention. From reading his post about how he intended it to work, it is very likely it is one of the first two. What I did was modify the SQLite queries to correctly detect lapsed cards and correctly calculate the success rate. I also added the option to allow the addon to work in the background without informing the user of the changes it made.
# Installation
Create a folder called `autoLapseNewInterval` inside `Anki2/addons21` and place `__init__.py` inside that folder.
# Usage
For more in-depth information on what the addon does, you should read [eshapard's original post](https://eshapard.github.io/anki/anki-auto-adjust-new-interval-after-a-lapse.html). 
You can adjust the `change_silently` variable in the code to allow the addon to make changes silently without prompting you.
