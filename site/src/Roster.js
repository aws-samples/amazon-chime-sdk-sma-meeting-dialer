import React from 'react';
import './App.css';
import { Roster, RosterGroup, RosterAttendee, useRosterState } from 'amazon-chime-sdk-component-library-react';
import { Container } from '@cloudscape-design/components';
import '@aws-amplify/ui-react/styles.css';
import '@cloudscape-design/global-styles/index.css';

const RosterContainer = () => {
    const { roster } = useRosterState();
    const attendees = Object.values(roster);
    const attendeeItems = attendees.map((attendee) => {
        const { chimeAttendeeId } = attendee || {};
        return <RosterAttendee key={chimeAttendeeId} attendeeId={chimeAttendeeId} name={attendee.externalUserId} />;
    });

    return (
        <Roster css={'padding-top: 20px; border: none; border-radius: 15px; background-color: #fff'}>
            <RosterGroup title={'Attendees'} css={''}>
                {attendeeItems}
            </RosterGroup>
        </Roster>
    );
};

export default RosterContainer;
