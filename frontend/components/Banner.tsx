import { Heading, Text } from '@chakra-ui/react';

export default function Banner() {
  return (
    <>
      <Heading size={'3xl'} textAlign={'center'}>
        Intelligent summaries for your meetings. In one click.
      </Heading>
      <Text fontSize={'xl'} marginTop={'8'} textAlign={'center'}>
        Scribe is an AI note-taker for all your meetings.
      </Text>
      <Text fontSize={'xl'} marginBottom={'8'} textAlign={'center'}>
        Choose a recording, and Scribe will deliver a smart summary plus a
        transcript in your inbox.
      </Text>
    </>
  );
}
