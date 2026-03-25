run('secrets.m');

% Read CO2 from Channel A (Field 1)
co2 = thingSpeakRead(channelA_ID, 'Fields', 1, 'NumPoints', 1, 'ReadKey', readKeyA);

% Read Temperature from Channel B (Field 1)
temp = thingSpeakRead(channelB_ID, 'Fields', 1, 'NumPoints', 1, 'ReadKey', readKeyB);

% Read Window status from Channel D (Field 1): 1 = open, 0 = closed
[windowStatus, timestamps] = thingSpeakRead(channelD_ID, 'Fields', 1, 'NumPoints', 1, 'ReadKey', readKeyD);

% Check if window was opened within the last 15 minutes
windowOpenRecently = false;
if windowStatus == 1
    windowOpenTime = timestamps;
    minutesAgo = minutes(datetime('now','TimeZone','UTC') - windowOpenTime);
    if minutesAgo <= 15
        windowOpenRecently = true;
    end
end

% Fan logic:
%   1) CO2 > 1000 
%   2) Window opened within last 15 min → fan ON (ventilation assist)
if (co2 > 1000 ) || windowOpenRecently
    fanCommand = 1;
else
    fanCommand = 0;
end

% Write result to Channel C
thingSpeakWrite(channelC_ID, fanCommand, 'WriteKey', writeKeyC);

disp(['CO2: ', num2str(co2), ' | Temp: ', num2str(temp), ...
      ' | Window: ', num2str(windowStatus), ' | Fan: ', num2str(fanCommand)]);