// export async function sendChatRequest(newMessages: any[], currentChatId: number | undefined){
export async function sendChatRequest(message: any[], chatId?: number,){
  const url = chatId ? `/api/chat/${chatId}` : `/api/chat`
    try {
        const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: message.map(({id, ...rest }) => rest),
          chat_id: chatId,
          // attachment: userMessage.attachment ?? null,
        }),
      })
      if (!response.ok || !response.body) {
        const errorText = await response.text()
        throw new Error(`Server error: ${errorText || response.statusText}`)
      }

      const reader = response.body.getReader()                                                                                                                                           
      const decoder = new TextDecoder()
      let responseText = ''

      while (true) { 
        const { value, done } = await reader.read()
        if (done) break
        responseText += decoder.decode(value)
      } 
      return JSON.parse(responseText);
  } catch(error){
    console.error('An error occurred during the request:', error)
    return{
      error: "죄송합니다. 답변 생성 중 오류가 발생했습니다.",
    };
  } 
}