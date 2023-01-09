import React, { useState } from 'react';
import './App.css';
import {
    useAudioVideo,
    useMeetingManager,
    ControlBar,
    ControlBarButton,
    Meeting,
    LeaveMeeting,
    AudioInputControl,
    Input,
    // DeviceLabels,
    Remove,
    VideoInputControl,
    AudioOutputControl,
} from 'amazon-chime-sdk-component-library-react';
import { API, Auth } from 'aws-amplify';
import '@aws-amplify/ui-react/styles.css';
import '@cloudscape-design/global-styles/index.css';

import { Loader } from '@aws-amplify/ui-react';

const MeetingControlBar = ({ meetingId }) => {
    // const [requestId, setRequestId] = useState('');
    const audioVideo = useAudioVideo();
    const meetingManager = useMeetingManager();
    const [isLoading, setLoading] = useState(false);

    // const JoinButtonProps = {
    //     icon: <Meeting />,
    //     onClick: (event) => handleJoin(event),
    //     label: 'Join',
    // };

    const LeaveButtonProps = {
        icon: <LeaveMeeting />,
        onClick: (event) => handleLeave(event),
        label: 'Leave',
    };

    const EndButtonProps = {
        icon: <Remove />,
        onClick: (event) => handleEnd(event),
        label: 'End',
    };

    const handleLeave = async (event) => {
        await meetingManager.leave();
    };

    const handleEnd = async (event) => {
        console.log(`Auth ${JSON.stringify(await Auth.currentUserInfo())}`);
        event.preventDefault();
        try {
            await API.post('meetingAPI', 'end', { body: { meetingId: meetingId } });
        } catch (err) {
            console.log(`{err in handleEnd: ${err}`);
        }
    };

    return (
        <ControlBar showLabels={true} responsive={true} layout="undocked-horizontal">
            {/* <Input
                showClear={true}
                onChange={(e) => setRequestId(e.target.value)}
                sizing={'md'}
                value={requestId}
                placeholder="Request ID"
                type="text"
            />
            {!audioVideo && <ControlBarButton {...JoinButtonProps} />} */}
            {isLoading && <Loader />}
            {audioVideo && (
                <>
                    <ControlBarButton {...LeaveButtonProps} />
                    <ControlBarButton {...EndButtonProps} />
                    <AudioInputControl />
                    <AudioOutputControl />
                    <VideoInputControl />
                </>
            )}
        </ControlBar>
    );
};

export default MeetingControlBar;
