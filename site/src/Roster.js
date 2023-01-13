import React, { useEffect, useState } from 'react';
import './App.css';
import {
    useAudioVideo,
    useMeetingManager,
    Roster,
    RosterGroup,
    RosterAttendee,
    RosterHeader,
    RosterCell,
    useRosterState,
} from 'amazon-chime-sdk-component-library-react';
import { Container } from '@cloudscape-design/components';
import '@aws-amplify/ui-react/styles.css';
import '@cloudscape-design/global-styles/index.css';

const RosterContainer = ({ meetingId }) => {
    const { roster } = useRosterState();
    const attendees = Object.values(roster);
    console.log(`Attendees: ${JSON.stringify(attendees)}`);
    const attendeeItems = attendees.map((attendee) => {
        const { chimeAttendeeId } = attendee || {};
        return <RosterAttendee key={chimeAttendeeId} attendeeId={chimeAttendeeId} name={attendee.externalUserId} />;
    });

    return (
        <Container>
            <Roster>
                <Roster>
                    <RosterGroup>{attendeeItems}</RosterGroup>
                </Roster>
            </Roster>
        </Container>
    );
};

export default RosterContainer;
