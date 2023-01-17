import React, { useEffect, useState } from 'react';
import './App.css';
import {
    useLocalVideo,
    useAudioVideo,
    useMeetingManager,
    VideoTileGrid,
    useMeetingStatus,
    DeviceLabels,
    MeetingStatus,
} from 'amazon-chime-sdk-component-library-react';
import '@aws-amplify/ui-react/styles.css';
import '@cloudscape-design/global-styles/index.css';
import { MeetingSessionConfiguration } from 'amazon-chime-sdk-js';
import MeetingControlBar from './MeetingControlBar';
import RosterContainer from './Roster';
import { API, Auth } from 'aws-amplify';
import { Container, SpaceBetween } from '@cloudscape-design/components';
import { useSearchParams } from 'react-router-dom';

const VideoMeeting = ({}) => {
    const meetingStatus = useMeetingStatus();
    const { toggleVideo } = useLocalVideo();
    const audioVideo = useAudioVideo();
    const meetingManager = useMeetingManager();
    const [search, setSearch] = useSearchParams();
    const [meetingId, setMeetingId] = useState('');

    useEffect(() => {
        async function joinMeeting() {
            const phoneNumber = (await Auth.currentUserInfo()).attributes.phone_number;
            const name = (await Auth.currentUserInfo()).attributes.given_name;
            console.log(search.get('eventId'));
            console.log(search.get('passcode'));
            try {
                const joinResponse = await API.post('meetingAPI', 'join', {
                    body: {
                        name: name,
                        PhoneNumber: phoneNumber,
                        EventId: search.get('eventId'),
                        MeetingPasscode: search.get('passcode'),
                    },
                });
                const meetingSessionConfiguration = new MeetingSessionConfiguration(
                    joinResponse.Meeting,
                    joinResponse.Attendee,
                );

                const options = {
                    deviceLabels: DeviceLabels.AudioAndVideo,
                };

                await meetingManager.join(meetingSessionConfiguration, options);
                await meetingManager.start();
                meetingManager.invokeDeviceProvider(DeviceLabels.AudioAndVideo);
                setMeetingId(joinResponse.Meeting.MeetingId);
            } catch (err) {
                console.log(`err in handleJoin: ${err}`);
            }
        }
        joinMeeting();
    }, []);

    useEffect(() => {
        async function tog() {
            if (meetingStatus === MeetingStatus.Succeeded) {
                await toggleVideo();
            }
            if (meetingStatus === MeetingStatus.Ended) {
            } else {
            }
        }
        tog();
    }, [meetingStatus]);

    return (
        <div className="MeetingContainer">
            {audioVideo && (
                <>
                    <SpaceBetween direction="horizontal" size="l">
                        <RosterContainer meetingId={meetingId} />
                        <Container footer={<MeetingControlBar meetingId={meetingId} />}>
                            <div style={{ height: '600px', width: '720px' }}>
                                <VideoTileGrid />
                            </div>
                        </Container>
                    </SpaceBetween>
                </>
            )}
        </div>
    );
};

export default VideoMeeting;
