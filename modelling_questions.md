# Modelling questions before training

These are genuine modelling choices. They should be agreed before a learning environment is treated as the project solution.

1. For the first experiment, should the model be one representative day only, or should it already include multi-day rules such as “scooter every five days” and “dishwasher once every two days”?
2. When battery energy is insufficient, which loads have priority? For example, should refrigerator always be supplied before TV/PC, AC, or flexible tasks?
3. Does the 5 kW generator always run at full power for a whole 30-minute block, or may it stop partway through a block as soon as the battery is full?
4. Should the overnight 23:00–09:00 block aggregate solar output from the early morning solar timetable, or should solar be counted only in the daytime blocks?
5. Should the fixed oven times be strict compulsory operation times, or allowed windows in which the agent can choose a start time?
6. Are the appliance powers and fixed durations final, or should they be treated as example parameters?
7. Which month/location should be used for the initial experiment? The supplied monthly maximum-output table can be used directly, but the location is not yet specified.
8. Do you prefer the first model to use only synthetic variation from the supplied ranges, or should we later calibrate it with a UK solar/weather dataset?
9. Are the proposed bins in `config.json` suitable for the two solar forecast variables?
10. If a running fixed-duration appliance is turned off, should it pause and retain its remaining time, cancel the task, or should turning it off be prohibited?

Resolved: single-day planning; fridge before fixed tasks before TV/AC; generator stops on fullness and overnight; overnight includes morning solar; tasks pause/resume; supplied London solar with June first; separate solar bins.


Assumptions for further review:

1. Fixed-task ties use laundry, dishwasher, oven; comfort ties use TV before AC. Can deadlines be used to further decide ties?
2. Scooter is placed last in the priority.
3. Zero solar shares the first bin.
4. New oven cycles remain agent choices at 11:30 or 17:00; paused cycles can resume later during daytime.
5. The overnight aggregate cannot detect shortages before morning solar arrives. Finer time resolution is future work.
6. Supplied powers, durations and noise ranges are retained. Calibration against measured data is future work.

The existing compact state omits explicit AC/scooter switches and oven cycle count.