import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './App.css';
import {
    useMeetingManager,
    ControlBar,
    ControlBarButton,
    LeaveMeeting,
    AudioInputControl,
    Remove,
    VideoInputControl,
    AudioOutputControl,
} from 'amazon-chime-sdk-component-library-react';
import { API, Auth } from 'aws-amplify';
import '@aws-amplify/ui-react/styles.css';
import '@cloudscape-design/global-styles/index.css';

const MeetingControlBar = ({ meetingId }) => {
    const meetingManager = useMeetingManager();
    const navigate = useNavigate();

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
        navigate('/', { replace: true });
    };

    const handleEnd = async (event) => {
        console.log(`Auth ${JSON.stringify(await Auth.currentUserInfo())}`);
        event.preventDefault();
        try {
            await API.post('meetingAPI', 'end', { body: { meetingId: meetingId } });
        } catch (err) {
            console.log(`{err in handleEnd: ${err}`);
        }
        navigate('/', { replace: true });
    };

    return (
        <ControlBar showLabels={true} responsive={true} layout="undocked-horizontal">
            <ControlBarButton {...LeaveButtonProps} />
            <ControlBarButton {...EndButtonProps} />
            <AudioInputControl />
            <AudioOutputControl />
            <VideoInputControl />
        </ControlBar>
    );
};

export default MeetingControlBar;
