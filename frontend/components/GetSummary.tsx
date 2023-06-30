import { FormEvent, useState, useRef } from 'react';
import { FormEventHandler } from 'react';

import { useUser } from '@/utils/useUser';

import { ProductWithPrice } from 'types';

import {
  Button,
  Alert,
  AlertIcon,
  AlertDescription,
  AlertTitle,
  Progress,
  Heading,
  Link,
  Text
} from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';

interface Props {
  products: ProductWithPrice[];
}

type BillingInterval = 'year' | 'month';

// Import React FilePond
import { FilePond, registerPlugin } from 'react-filepond';

import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type';

// Import FilePond styles
import 'filepond/dist/filepond.min.css';
import Banner from './Banner';

registerPlugin(FilePondPluginFileValidateType);

export default function GetSummary() {
  const [billingInterval, setBillingInterval] =
    useState<BillingInterval>('month');
  const [priceIdLoading, setPriceIdLoading] = useState<string>();
  const { user, isLoading, subscription, accessToken } = useUser();

  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const fileInput = useRef<FilePond>(null);

  const handleSubmit: FormEventHandler<HTMLFormElement> = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    // Stop the form from submitting and refreshing the page.
    event.preventDefault();

    if (!user) {
      setError('You are not logged in, please sign in.');
      return;
    }

    setLoading(true);

    // Check if the user has a subscription.
    if (!subscription) {
      setError(
        'You do not have a subscription. Please subscribe to get access to Scribe.'
      );
      setLoading(false);
      return;
    }

    // Check if the user has enough credits.
    if (subscription.credits === undefined || subscription.credits < 1) {
      setError(
        "You don't have any summaries left in this month. Please upgrade your plan to get more."
      );
      setLoading(false);
      return;
    }

    const formData = new FormData();

    // Get data from the form.
    if (fileInput.current?.getFiles().length === 0) {
      setError('Please select a file to upload.');
      setLoading(false);
      return;
    }
    formData.append('file', fileInput.current?.getFile().file as Blob);

    // API endpoint where we send form data.
    const endpoint = `/api/submit/`;

    // Get the user's JWT token from Supabase.
    if (!accessToken) {
      setError('You are not logged in.');
      setLoading(false);
      return;
    }

    // Form the request for sending data to the server.
    const options = {
      method: 'POST',
      body: formData,
      headers: {
        Authorization: `Bearer ${accessToken}`
      }
    };

    // Send the request to the server.
    let response;
    try {
      response = await fetch(endpoint, options);
    } catch (error) {
      setError('Error connecting to the server. Please try again later.');
      setLoading(false);
      return;
    }

    if (response.status === 413) {
      setError(
        'Your file is too large. Please upload a file less than 100 MB.'
      );
      setLoading(false);
      return;
    }

    if (response.status !== 202) {
      setError('Something went wrong. Please try again.');
      setLoading(false);
      return;
    }

    // Get the response data from server as JSON.
    const result = await response.json();

    // If the response is 202, that means the file was queued to be processed.
    if (response.status == 202) {
      setSuccess(true);
      // Update local data.
      subscription.credits = subscription.credits - 1;
    } else {
      setError(result.message || 'Something went wrong. Please try again.');
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col p-8 justify-center min-h-screen">
      <Banner />
      <div className="h-[350px]">
        {success && (
          <div className="flex flex-col gap-6 justify-center items-center">
            <Alert
              status="success"
              variant="left-accent"
              flexDirection="column"
              alignItems="center"
              justifyContent="center"
              textAlign="center"
              height="200px"
            >
              <AlertIcon boxSize="40px" mr={0} />
              <AlertTitle mt={4} mb={1} fontSize="lg">
                Well done!
              </AlertTitle>
              <AlertDescription maxWidth="lg">
                We'll email you the summary as soon as it's ready. It should
                land in your inbox within 24 hours, although it's usually much
                quicker.
              </AlertDescription>
            </Alert>
            <Button
              onClick={() => {
                setSuccess(false);
              }}
            >
              Generate one more summary
            </Button>
          </div>
        )}
        {error && (
          <div className="flex flex-col gap-6 justify-center items-center">
            <Alert status="error" variant="left-accent">
              <AlertIcon />
              <div className="flex flex-col">
                <div>{error}</div>
                <div>
                  If error persists, please contact us{' '}
                  <Link
                    isExternal
                    style={{ textDecoration: 'underline' }}
                    href="mailto:tryscribe@gmail.com"
                  >
                    here
                  </Link>
                  .
                </div>
              </div>
            </Alert>
            <Button
              leftIcon={<RepeatIcon />}
              onClick={() => {
                setError('');
              }}
            >
              Try again
            </Button>
          </div>
        )}
        {loading && (
          <div className="flex justify-center flex-col items-center gap-8 mt-6">
            <Text fontSize={'lg'}>
              Uploading the file, this might take up to 5 minutes, hang tight...
            </Text>
            <Progress size="xs" width={'md'} isIndeterminate />{' '}
          </div>
        )}
        {!success && !error && !loading && (
          <form onSubmit={handleSubmit} encType="multipart/form-data">
            <FilePond
              ref={fileInput}
              required={true}
              storeAsFile={true}
              acceptedFileTypes={['audio/*', 'video/*', 'text/plain']}
              name="files" /* sets the file input name, it's filepond by default */
              labelIdle='Drag & Drop the recording of your meeting or <span class="filepond--label-action">Browse</span> <br/> We support audio, video and text files up to 300MB.'
              credits={false}
            />
            <div className="flex justify-center pt-8">
              <Button
                type="submit"
                bgGradient={'linear(to-r, #7928CA, #FF0080)'}
                padding={'10px 40px'}
                rounded={'full'}
                textColor="white"
                _hover={{
                  bgGradient: 'linear(to-r, #7928CA, #FF0080)',
                  opacity: 0.8
                }}
              >
                Genereate Summary
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
