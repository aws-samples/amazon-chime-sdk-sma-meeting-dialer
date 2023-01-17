import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import './App.css';
import '@aws-amplify/ui-react/styles.css';
import '@cloudscape-design/global-styles/index.css';
import { Container, Input, Button, SpaceBetween, Header } from '@cloudscape-design/components';

const JoinMeeting = ({}) => {
    const [passcode, setPasscode] = React.useState('');
    const [eventId, setEventId] = React.useState('');

    return (
        <div style={{ paddingLeft: '20px', height: '600px', width: '720px' }}>
            <Container header={<Header variant="h2">Join Meeting</Header>}>
                <SpaceBetween direction="horizontal" size="l">
                    <Input
                        inputMode="numeric"
                        type="number"
                        onChange={({ detail }) => setEventId(detail.value)}
                        placeholder="Enter Event ID"
                        value={eventId}
                    />
                    <Input
                        type="number"
                        inputMode="numeric"
                        onChange={({ detail }) => setPasscode(detail.value)}
                        placeholder="Enter Passcode"
                        value={passcode}
                    />
                    <Link to={`/meeting?eventId=${eventId}&passcode=${passcode}`}>
                        <Button>Join</Button>
                    </Link>
                </SpaceBetween>
            </Container>
        </div>
    );
};

export default JoinMeeting;
