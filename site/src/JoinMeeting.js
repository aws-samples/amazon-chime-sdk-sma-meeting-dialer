import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { API } from 'aws-amplify';
import './App.css';
import '@aws-amplify/ui-react/styles.css';
import '@cloudscape-design/global-styles/index.css';
import {
    Container,
    Input,
    Button,
    SpaceBetween,
    Header,
    Form,
    FormField,
    Checkbox,
    Flashbar,
} from '@cloudscape-design/components';

const JoinMeeting = ({}) => {
    const [passcode, setPasscode] = useState('');
    const [eventId, setEventId] = useState('');
    const [attendeeName, setAttendeeName] = useState('');
    const [attendeePhoneNumber, setAttendeePhoneNumber] = useState('');
    const [attendeeEmail, setAttendeeEmail] = useState('');
    const [attendeeCall, setAttendeeCall] = useState(false);
    const [attendeeCreated, setAttendeeCreated] = useState(false);
    const [errorCreating, setErrorCreating] = useState(false);
    const navigate = useNavigate();

    const handleCreate = async (event) => {
        event.preventDefault();
        console.log('Handling Create');
        if (!(eventId && attendeeName && attendeePhoneNumber)) {
            setErrorCreating(true);
        } else {
            setErrorCreating(false);
            try {
                const createResponse = await API.post('meetingAPI', 'create', {
                    body: {
                        attendeeName: attendeeName,
                        attendeeEmail: attendeeEmail,
                        attendeePhoneNumber: attendeePhoneNumber,
                        attendeeCall: attendeeCall,
                        eventId: eventId,
                    },
                });
                if (createResponse) {
                    setAttendeeCreated(true);
                }
                setPasscode(createResponse.passcode);
            } catch (err) {
                console.log(`{err in handleEnd: ${err}`);
            }
        }
    };

    const handleJoin = async (event) => {
        event.preventDefault();
        navigate(`/meeting?eventId=${eventId}&passcode=${passcode}`, { replace: true });
    };

    return (
        <div style={{ paddingLeft: '20px', height: '600px', width: '720px' }}>
            <SpaceBetween direction="vertical" size="l">
                <Container header={<Header variant="h2">Join Existing Meeting</Header>}>
                    <SpaceBetween direction="vertical" size="l">
                        <form
                            onSubmit={(e) => {
                                handleJoin(e);
                            }}
                        >
                            <Form
                                actions={
                                    <Button iconName="group-active" variant="primary">
                                        Join
                                    </Button>
                                }
                            >
                                <FormField>
                                    <SpaceBetween direction="vertical" size="s">
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
                                    </SpaceBetween>
                                </FormField>
                            </Form>
                        </form>
                    </SpaceBetween>
                </Container>
                <Container header={<Header variant="h2">Create Meeting/Attendee</Header>}>
                    {errorCreating && (
                        <Flashbar
                            items={[
                                {
                                    type: 'error',
                                    dismissible: true,
                                    statusIconAriaLabel: 'error',
                                    dismissLabel: 'Dismiss message',
                                    content: `Missing required fields: ${eventId ? '' : 'Event ID, '} ${
                                        attendeeName ? '' : 'Attendee Name, '
                                    }  ${attendeePhoneNumber ? '' : 'Attendee Phone Number'}`,
                                    onDismiss: () => setErrorCreating(false),
                                    id: 'errorFlashMessageId',
                                },
                            ]}
                        />
                    )}
                    {attendeeCreated && (
                        <Flashbar
                            items={[
                                {
                                    type: 'success',
                                    dismissible: true,
                                    statusIconAriaLabel: 'success',
                                    dismissLabel: 'Dismiss message',
                                    content: `Successfully created Attendee: ${attendeeName}.`,
                                    onDismiss: () => setAttendeeCreated(false),
                                    id: 'successFlashMessageId',
                                },
                            ]}
                        />
                    )}

                    <form
                        onSubmit={(e) => {
                            handleCreate(e);
                        }}
                    >
                        <Form
                            actions={
                                <Button iconName="user-profile-active" variant="primary">
                                    Create
                                </Button>
                            }
                        >
                            <FormField>
                                <SpaceBetween direction="vertical" size="s">
                                    <Input
                                        value={eventId}
                                        onChange={(event) => setEventId(event.detail.value)}
                                        placeholder="Enter Event ID"
                                    />
                                    <Input
                                        value={attendeeName}
                                        onChange={(event) => setAttendeeName(event.detail.value)}
                                        placeholder="Enter Attendee Name"
                                    />
                                    <Input
                                        value={attendeePhoneNumber}
                                        onChange={(event) => setAttendeePhoneNumber(event.detail.value)}
                                        placeholder="Enter Attendee Phone Number"
                                        inputMode="tel"
                                    />
                                    <Input
                                        value={attendeeEmail}
                                        onChange={(event) => setAttendeeEmail(event.detail.value)}
                                        placeholder="Enter Attendee Email"
                                        type="email"
                                        inputMode="email"
                                    />
                                    <Checkbox
                                        onChange={({ detail }) => setAttendeeCall(detail.checked)}
                                        checked={attendeeCall}
                                    >
                                        Call Attendee
                                    </Checkbox>
                                </SpaceBetween>
                            </FormField>
                        </Form>
                    </form>
                </Container>
            </SpaceBetween>
        </div>
    );
};

export default JoinMeeting;
