import { Formik, Field, Form } from 'formik';
import { User } from '@supabase/auth-helpers-nextjs';
import { UserDetails } from '@/types';
import {
  FormControl,
  FormLabel,
  FormErrorMessage,
  FormHelperText,
  Heading,
  Input,
  Button,
  useToast,
  ToastId
} from '@chakra-ui/react';
import * as Yup from 'yup';
import {
  updateUserEmail,
  updateUserName,
  updateUserPassword
} from '@/utils/supabase-client';
import { useRef } from 'react';

const AccountSchema = Yup.object().shape({
  fullName: Yup.string().trim(),
  email: Yup.string().email('Invalid email').required('Required'),
  password: Yup.string().min(6, 'Too Short!').max(50, 'Too Long!')
});

export default function AccountForm({
  user,
  userDetails
}: {
  user: User;
  userDetails: UserDetails;
}) {
  const toast = useToast();
  const toastIdRef = useRef<ToastId>();
  function addToast(title: string, status?: 'success' | 'error' | 'info') {
    toastIdRef.current = toast({
      title: title,
      status: status,
      duration: 5000,
      isClosable: true,
      variant: 'left-accent',
      position: 'bottom-right'
    });
  }
  return (
    <div className="flex justify-center flex-col gap-8">
      <Heading>Personal Details</Heading>
      <Formik
        initialValues={{
          fullName: userDetails.full_name,
          email: user.email,
          password: ''
        }}
        validationSchema={AccountSchema}
        onSubmit={async (values, actions) => {
          try {
            if (values.email !== undefined && values.email !== user.email) {
              await updateUserEmail(values.email);
              addToast(
                'Check both your old and new email to confirm your new email address',
                'info'
              );
            }
            if (
              values.fullName !== undefined &&
              values.fullName !== userDetails.full_name
            ) {
              await updateUserName(user, values.fullName);
              addToast('Details updated', 'success');
            }
            if (values.password !== '') {
              await updateUserPassword(values.password);
              addToast('Password updated', 'success');
            }
            actions.resetForm({ values });
          } catch (error: any) {
            addToast(error.message, 'error');
          }
        }}
      >
        {({ handleSubmit, errors, touched, values, isSubmitting, dirty }) => (
          <Form className="flex flex-col gap-6">
            <FormControl>
              <FormLabel>Full name</FormLabel>
              <Field as={Input} name="fullName" />
              <FormErrorMessage>{errors.fullName}</FormErrorMessage>
            </FormControl>
            <FormControl isInvalid={!!errors.email && touched.email}>
              <FormLabel>Your email</FormLabel>
              <Field as={Input} name="email" type="email" />
              <FormErrorMessage>{errors.email}</FormErrorMessage>
            </FormControl>
            <FormControl>
              <FormLabel>Your password</FormLabel>
              <Field as={Input} name="password" />
              <FormErrorMessage>{errors.password}</FormErrorMessage>
            </FormControl>
            <Button isLoading={isSubmitting} isDisabled={!dirty} type="submit">
              Update
            </Button>
          </Form>
        )}
      </Formik>
    </div>
  );
}
