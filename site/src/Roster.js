import React, { useEffect, useState } from 'react';
import './App.css';
import { Roster, RosterGroup, RosterAttendee, useRosterState } from 'amazon-chime-sdk-component-library-react';
import '@aws-amplify/ui-react/styles.css';
import '@cloudscape-design/global-styles/index.css';
import { API } from 'aws-amplify';

const RosterContainer = (meetingId) => {
    const { roster } = useRosterState();
    const rosterAttendees = Object.values(roster);
    const [mergedAttendees, setMergedAttendees] = useState([]);
    let attendees = [];

    useEffect(() => {
        async function queryMeeting() {
            console.log(`MeetingId:  ${JSON.stringify(meetingId)}`);
            if (meetingId.meetingId !== '') {
                const queriedAttendees = await API.post('meetingAPI', 'query', {
                    body: { meetingId: meetingId.meetingId },
                });
                console.log(`Queried Attendees:  ${JSON.stringify(queriedAttendees)}`);
                console.log(`Roster Attendees:  ${JSON.stringify(rosterAttendees)}`);
                for (let i = 0; i < rosterAttendees.length; i++) {
                    console.log(`RosterAttendeeFor:  ${JSON.stringify(rosterAttendees[i])}`);
                    console.log(`QueriedAttendeeFor:  ${JSON.stringify(queriedAttendees)}`);
                    attendees.push({
                        ...rosterAttendees[i],
                        ...queriedAttendees.find(
                            (attendee) => attendee.AttendeeId === rosterAttendees[i].chimeAttendeeId,
                        ),
                    });
                }
                console.log(`MergedAttendees:   ${JSON.stringify(attendees)}`);

                setMergedAttendees(attendees);
            }
        }
        queryMeeting();
    }, [roster]);

    const attendeeItems = mergedAttendees.map((attendee) => {
        console.log(`Attendee:  ${JSON.stringify(attendee)}`);
        return (
            <RosterAttendee
                key={attendee.AttendeeId}
                attendeeId={attendee.AttendeeId}
                name={attendee.Name}
                subtitle={attendee.JoinMethod}
            />
        );
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
