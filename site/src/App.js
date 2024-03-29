import React, { useState, useEffect } from 'react';
import './App.css';
import { Amplify, Auth, API } from 'aws-amplify';
import { AmplifyConfig } from './Config';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import '@cloudscape-design/global-styles/index.css';
import VideoMeeting from './VideoMeeting';
import JoinMeeting from './JoinMeeting';
import { MeetingProvider } from 'amazon-chime-sdk-component-library-react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';

import { ContentLayout, Header, SpaceBetween, Button } from '@cloudscape-design/components';

Amplify.configure(AmplifyConfig);
API.configure(AmplifyConfig);
Amplify.Logger.LOG_LEVEL = 'DEBUG';

const App = () => {
    // const [currentCredentials, setCurrentCredentials] = useState({});
    // const [currentSession, setCurrentSession] = useState({});

    // useEffect(() => {
    //     console.log(`useEffect: currentCredentials: ${JSON.stringify(currentCredentials)}`);
    //     console.log(`useEffect: currentSession: ${JSON.stringify(currentSession)}`);

    //     async function getAuth() {
    //         setCurrentSession(await Auth.currentSession());
    //         setCurrentCredentials(await Auth.currentUserCredentials());
    //         console.log(`authState: ${JSON.stringify(currentSession)}`);
    //         console.log(`currentCredentials: ${JSON.stringify(currentCredentials)}`);
    //     }
    //     getAuth();
    // }, []);

    const formFields = {
        signUp: {
            email: {
                order: 1,
                isRequired: true,
            },
            given_name: {
                order: 2,
                isRequired: true,
                placeholder: 'Name',
            },
            phone_number: {
                order: 3,
                isRequired: true,
                placeholder: 'Phone Number',
            },
            password: {
                order: 4,
            },
            confirm_password: {
                order: 5,
            },
        },
    };

    return (
        <Authenticator loginMechanisms={['email']} formFields={formFields}>
            {({ signOut, user }) => (
                <MeetingProvider>
                    <ContentLayout
                        header={
                            <SpaceBetween size="m">
                                <Header
                                    className="ContentHeader"
                                    variant="h2"
                                    actions={
                                        <Button variant="primary" onClick={signOut}>
                                            Sign out
                                        </Button>
                                    }
                                >
                                    Amazon Chime SDK Meeting
                                </Header>
                            </SpaceBetween>
                        }
                    >
                        <Routes>
                            <Route exact path="/" element={<JoinMeeting />} />
                            <Route path="/meeting" element={<VideoMeeting />} />
                        </Routes>
                    </ContentLayout>
                </MeetingProvider>
            )}
        </Authenticator>
    );
};

export default App;
