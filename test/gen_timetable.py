import datetime

times_purple = []
times_purple.append(datetime.datetime.strptime('17:00', "%H:%M"))
while times_purple[-1] < datetime.datetime.strptime('20:45', "%H:%M"):
    times_purple.append(times_purple[-1] + datetime.timedelta(minutes=45))
times_purple.append(times_purple[-1] + datetime.timedelta(minutes=15))
while times_purple[-1] < datetime.datetime.strptime('22:30', "%H:%M"):
    times_purple.append(times_purple[-1] + datetime.timedelta(minutes=45))
times_purple.append(times_purple[-1] + datetime.timedelta(minutes=30))
i=0
while i < len(times_purple):
    times_purple[i] = times_purple[i].strftime("%H:%M")
    i += 1
print(times_purple)